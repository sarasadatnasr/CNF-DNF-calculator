import ply.lex as lex
import ply.yacc as yacc
import copy

# 1. Lexer

# 1.1 Tokens
tokens = (
    'Variable',
    'And',
    'Or',
    'Not',
    'Implication',
    'Left',
    'Right',
)
# 1.2 Declarations
# For std input : and: /\, or: \/, not: ~, implication: ->
# parentheses : (), variable examples: x1, X1, x, Y
t_And = r'[\s]*\/\\[\s]*'
t_Or = r'[\s]*\\/[\s]*'
t_Not = r'~'
t_Implication = r'->'
t_Left = r'\('
t_Right = r'\)'
t_ignore = ' '
t_Variable = '[a-zA-Z][0-9]*'


# A track of line numbers rule
def t_newline(t):
    r'\n+'
    t.lexer.lineno += len(t.value)


# Error rule
def t_error(t):
    print("Illegal character '%s'" % t.value[0])
    t.lexer.skip(1)


# 2. Yacc
# 2.1 Precedence of operators
precedence = (
    ('right', 'Implication'),
    ('left', 'Or'),
    ('left', 'And'),
    ('right', 'Not'),)


# 2.2 Grammar rules for variable and operators

# paranthesis expression rule Value = (Value)
def p_expression_group(t):
    'expression : Left expression Right'
    t[0] = t[2]


# Variable values for dictionary parsing rule
def p_expression_variable(t):
    '''expression : Variable'''
    # Value of variable
    t[0] = {'value': t[1]}


CNJ = '/\\'
DNJ = '\\/'


# Binary operators rules
def p_expression_binop(t):
    ''' expression : expression And expression
                    | expression Or expression
                    | expression Implication expression'''
    if t[2] == CNJ:
        t[0] = {'left': t[1], 'right': t[3], 'operator': CNJ}
    elif t[2] == DNJ:
        t[0] = {'left': t[1], 'right': t[3], 'operator': DNJ}
    elif t[2] == '->':
        temp = {'child': t[1], 'operator': '~'}
        t[0] = {'left': temp, 'right': t[3], 'operator': DNJ}


# Unary operator rule
def p_expression_negative(t):
    'expression : Not expression'
    t[0] = {'child': t[2], 'operator': '~'}


# Error parse rule
def p_error(t):
    print("Syntax error at '%s'" % t.value)


# 3. Simplificaton of the input expression

def IsNot(branch):
    if 'operator' in branch and branch['operator'] == '~':
        return True
    return False


def IsVariable(branch):
    return 'value' in branch or IsNot(branch)


def Var(branch):
    if 'value' in branch:
        return branch['value']
    elif IsNot(branch):
        return '~' + branch['child']['value']


def DeMorganLaws(branch):
    neg1 = {'child': branch['child']['left'], 'operator': '~'}
    neg2 = {'child': branch['child']['right'], 'operator': '~'}
    branch['child']['left'] = neg1
    branch['child']['right'] = neg2
    if branch['child']['operator'] == CNJ:
        branch['child']['operator'] = DNJ
    elif branch['child']['operator'] == DNJ:
        branch['child']['operator'] = CNJ
    return branch['child']


def Involution(branch):
    branch = branch['child']['child']
    return branch


# 3.1 Applying De Morgan's laws and involution

def Negation(Tree):
    if Tree == None:
        return
    if 'value' in Tree:
        return Tree
    if Tree['operator'] == '~' and 'operator' in Tree['child'] and \
            Tree['child']['operator'] != '~':
        # Cases ~(A\/B), ~(A/\B)
        Tree = DeMorganLaws(Tree)
        Tree['left'] = Negation(Tree['left'])
        Tree['right'] = Negation(Tree['right'])
    elif Tree['operator'] == '~' and 'operator' in Tree['child'] and Tree['child']['operator'] == '~':
        # Case ~(~X)
        Tree = Involution(Tree)
    elif Tree['operator'] == '~':
        # Deep test of ~; child - after ->
        Tree['child'] = Negation(Tree['child'])
    else:
        Tree['left'] = Negation(Tree['left'])
        Tree['right'] = Negation(Tree['right'])
    return Tree


def NeedDistrib(branch, symbol):
    if IsVariable(branch):
        return False
    if branch['operator'] == symbol:
        return False
    else:
        left = branch['left']
        right = branch['right']
        # Case a\/b\/c for cnj and (a/\b/\c) for dsj
        if IsVariable(left) and IsVariable(right):
            return False
        # Case a\/((e/\f)\/d) for cnj and (a/\((e\/f)/\d)) for dsj
        if 'operator' in left and left['operator'] == symbol:
            return True
        # Case a\/(d\/(e/\f)) for cnj and (a/\(d/\(e\/f))) for dsj
        if 'operator' in right and right['operator'] == symbol:
            return True
        return NeedDistrib(left, symbol) | NeedDistrib(right, symbol)


def opposite_symbol(symbol):
    if symbol == DNJ:
        return CNJ
    return DNJ


def Distribution(branch, symbol):
    # Comments for CNF
    # If (e/\f)\/d, then: (e\/d)/\(f\/d)
    notSymbol = opposite_symbol(symbol)
    if 'operator' in branch['left'] and branch['left']['operator'] == symbol:
        A = branch['left']['left']
        B = branch['left']['right']
        C = branch['right']
        branch['operator'] = symbol
        left = {'left': A, 'right': C, 'operator': notSymbol}
        right = {'left': B, 'right': C, 'operator': notSymbol}
        branch['left'] = left
        branch['right'] = right
        return branch
    # If d\/(e/\f), then: (d\/e)/\(d\/f)
    if 'operator' in branch['right'] and branch['right']['operator'] == symbol:
        A = branch['left']
        B = branch['right']['left']
        C = branch['right']['right']
        branch['operator'] = symbol
        left = {'left': A, 'right': B, 'operator': notSymbol}
        right = {'left': A, 'right': C, 'operator': notSymbol}
        branch['left'] = left
        branch['right'] = right
        return branch


# 3.2 Applying Distribution laws
def Symbol_Tree(Tree, symbol):
    # If only one pair ()
    if IsVariable(Tree):
        return Tree
    notSymbol = opposite_symbol(symbol)
    # If opposite symbol in Tree left branch DNJ (CNJ) check NeedDistrib
    if Tree['operator'] == notSymbol and 'operator' in Tree['left'] and Tree['left']['operator'] == notSymbol \
            and NeedDistrib(Tree['left'], symbol):
        Tree['left'] = Symbol_Tree(Tree['left'], symbol)

    # If opposite symbol in Tree right branch DNJ (CNJ) check NeedDistrib
    if Tree['operator'] == notSymbol and 'operator' in Tree['right'] and Tree['right']['operator'] == notSymbol and \
            NeedDistrib(Tree['right'], symbol):
        Tree['right'] = Symbol_Tree(Tree['right'], symbol)
    # If opposite symbol in Tree
    if NeedDistrib(Tree, symbol):
        Tree = Distribution(Tree, symbol)
        Tree['left'] = Symbol_Tree(Tree['left'], symbol)
        Tree['right'] = Symbol_Tree(Tree['right'], symbol)
    else:
        Tree['left'] = Symbol_Tree(Tree['left'], symbol)
        Tree['right'] = Symbol_Tree(Tree['right'], symbol)
    return Tree


# 3.3 Idempotency and Absorption laws

def Idempotency(Tree, symbol):
    # Idempotency A\/A = A
    for i in range(0, len(Tree)):
        k = list(set(Tree[i]))
        Tree[i] = sorted(k)
    Tree = sorted(Tree)
    Result = copy.deepcopy(Tree)
    for i in range(0, len(Tree) - 1):
        if (Tree[i] == Tree[i + 1]):
            Result.remove(Tree[i])
    Result = [set(i) for i in Result]
    Tree = Result
    Result = copy.deepcopy(Tree)
    # Absorption A\/(A/\B) = A
    for i in range(0, len(Tree)):
        for j in range(0, len(Tree)):
            if i != j and len(Tree[i]) < len(Tree[j]):
                if Tree[j] in Result and Tree[i].intersection(Tree[j]) == Tree[i]:
                    Result.remove(Tree[j])
    return Result


def Parsing_Parantheses(Tree, symbol):
    notSymbol = opposite_symbol(symbol)
    Result = ''
    for i in range(0, len(Tree)):
        if len(Tree[i]) != 1:
            Result += '('
            Result += notSymbol.join(list(Tree[i]))
            Result += ')'
        else:
            Result += ''.join(list(Tree[i]))
        if i != len(Tree) - 1:
            Result += symbol
    return Result


def to_form(Tree, symbol):
    if IsVariable(Tree):
        return [Var(Tree)]
    notSymbol = opposite_symbol(symbol)
    if Tree['operator'] == symbol:
        Result = []
        left = to_form(Tree['left'], symbol)
        right = to_form(Tree['right'], symbol)
        if isinstance(left[0], str):
            Result.append(left)
        else:
            for i in left:
                Result.append(i)
        if isinstance(right[0], str):
            Result.append(right)
        else:
            for i in right:
                Result.append(i)
        return Result
    else:
        Result = (to_form(Tree['left'], symbol)) + to_form(Tree['right'], symbol)
        return Result


def Parse_Tree(data):
    lexer = lex.lex()
    parser = yacc.yacc()
    return parser.parse(data)


def to_symbol_form(data, symbol):
    Tree = Parse_Tree(data)  # returns the parsed expression
    Tree = Negation(Tree)  # returns the tree with only unary ~
    Tree = Symbol_Tree(Tree, symbol)  # returns the tree after applied distribution laws
    # Case of only \/ or /\ in CNF and DNF respectively
    if Tree['operator'] != symbol:
        symbol = Tree['operator']
    # Returns the list of lists for sorting and idempotency rule
    Tree = to_form(Tree, symbol)
    Tree = Idempotency(Tree, symbol)  # returns result
    result = Parsing_Parantheses(Tree, symbol)
    return result


def to_CNF(data):
    return to_symbol_form(data, CNJ)


def to_DNF(data):
    return to_symbol_form(data, DNJ)


