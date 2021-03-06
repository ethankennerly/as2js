#coding: utf-8
"""
Converts some ActionScript3 to a JavaScript file.
Usage:  python as2js.py actionscriptFile.as [...]
    Overwrites each .js file parallel to each .as file.
Usage:  python as2js.py --test
    Just run unit tests.
Forked from 06\_jw as2js by Ethan Kennerly.
"""

import codecs
import os
import re
import textwrap

import as2js_cfg as cfg

literal = r'[\w\-\."\'\\]+'
argument = '(\w+)\s*(:\w+)?(\s*=\s*' + literal + ')?'
var = 'var'
varKeyword = r'(?:\bvar\b|\bconst\b)'
varEscape = '&'
varEscapeEscape = '<varEscapeEscape>'
notStatement = '[^;]+'
assignment = '(\w+)\s*(:\w+)?(\s*=\s*' + notStatement + ')?'
localVariable = varKeyword + '\s+' + assignment + ';?'
localVariableEscaped = '(' + varEscape + '\s+)' + argument

namespace = '(?:private|protected|public|internal)'
notStatic = '(?<!static\s)'
staticNamespace = '(?:' + 'static\s+' + namespace \
                  + '|' + namespace + '\s+static' + ')'
argumentP =  re.compile(argument, re.S)

commentEnd = '*/'
commentEndEscape = '~'
commentEndEscapeEscape = 'commentEndEscapeEscape'

comment =  '/\*[^' + commentEndEscape + ']+' + commentEndEscape
commentPrefix = '(\s*' + comment + '\s*)?'
functionPrefix = commentPrefix + '(?:override\s+)?' 
functionEnd = '}'
functionEndEscape = '@'
functionEndEscapeEscape = 'functionEndEscapeEscape'
function = 'function\s+(\w+)\s*\(([^\)]*)\)\s*(?::\s*[\w\*]+)?\s*{([^' + functionEndEscape + ']*?)' + functionEndEscape

staticPropP =  re.compile(commentPrefix
    + staticNamespace
    + '\s+' + localVariable, re.S)

vectorType = 'Vector\.<[^>]*>+'
vectorTypeP = re.compile(vectorType, re.S)
arrayType = 'Array'
vectorLiteral = 'new\s+<[^>]*>+'
vectorLiteralP = re.compile(vectorLiteral, re.S)
vectorConstructor = 'new\s+Vector\.<[^>]*>+\(\d*\)'
vectorConstructorP = re.compile(vectorConstructor, re.S)
arrayConstructor = 'new Array()'


def staticProps(klassName, klassContent):
    r"""
    Declared, defined variable without a space.
    >>> staticProps('FlxBasic', 'static internal var _VISIBLECOUNT:uint= 5;')
    'FlxBasic._VISIBLECOUNT= 5;'

    Declared, undefined variable.
    >>> staticProps('FlxBasic', 'static internal var _ACTIVECOUNT:uint;')
    'FlxBasic._ACTIVECOUNT;'

    Namespace first. 
    Defining an array of objects and an inline comment.
    Do not replace object key (if a colon follows).
    >>> print staticProps('View', 'private static var i:int;\nprivate static var items:Array=[{a: 1},//1\n{b: 2, i: i}];')
    View.i;
    View.items=[{a: 1},//1
    {b: 2, i: View.i}];

    Declared, undefined variable.
    >>> staticProps('FlxBasic', 'public static var _ACTIVECOUNT:uint;')
    'FlxBasic._ACTIVECOUNT;'

    No namespace not supported.
    >>> staticProps('FlxBasic', 'static var _ACTIVECOUNT:uint;')
    ''

    Constant.
    >>> staticProps('FlxBasic', 'public static const ACTIVECOUNT:uint;')
    'FlxBasic.ACTIVECOUNT;'

    Block comment.
    >>> print staticProps('FlxBasic', '/* how many */\npublic static const ACTIVECOUNT:uint;')
    /* how many */
    FlxBasic.ACTIVECOUNT;

    Block comment.
    >>> print staticProps('FlxBasic', '/* not me */\npublic const NOTME:uint;/* how many */\npublic static const ACTIVECOUNT:uint;')
    /* how many */
    FlxBasic.ACTIVECOUNT;
    """
    staticProps = _parseProps(klassName, klassContent, staticPropP)
    strs = []
    for comment, name, dataType, definition in staticProps:
        line = ''
        if comment:
            line = comment
        line += klassName + '.' + name + definition + ';'
        strs.append(line)
    return '\n'.join(strs)


def _escapeFunctionEnd(klassContent):
    """
    Escape end of outermost scope function.
    This makes a regular expression simple search until next character.
    Stack each open bracket and escape 0th stack closing bracket.
    >>> _escapeFunctionEnd('private static function f(){function g(){}}')
    'private static function f(){function g(){}@'

    Escape escape the raw escape character.
    >>> _escapeFunctionEnd('private static function f(@){function g(){}}')
    'private static function f(functionEndEscapeEscape){function g(){}@'

    Assumes matching parentheses.
    >>> _escapeFunctionEnd('}{function g(){}}')
    '}{function g(){@}'
    """
    escaped = klassContent.replace(functionEndEscape, functionEndEscapeEscape)
    characters = []
    characters += escaped
    blockBegin = '{'
    depth = 0
    for c, character in enumerate(characters):
        if blockBegin == character:
            depth += 1
        elif functionEnd == character:
            depth -= 1
            if 0 == depth:
                characters[c] = functionEndEscape
    return ''.join(characters)


def _escapeEnds(original):
    """Comment, function end.
    Escape comment end, because non-greedy becomes greedy in context.  Example:
    blockCommentNonGreedy = '(\s*/\*[\s\S]+?\*/\s*){0,1}?'
    """
    original = _escapeWildCard(original)
    commentEscaped = original \
        .replace(commentEndEscape, commentEndEscapeEscape) \
        .replace(commentEnd, commentEndEscape)
    return _escapeFunctionEnd(commentEscaped)


def _unescapeEnds(safe):
    """Comment, function end.
    >>> _unescapeEnds('functionEndEscapeEscape{@')
    '@{}'
    """
    return safe.replace(commentEndEscape, commentEnd) \
        .replace(commentEndEscapeEscape, commentEndEscape) \
        .replace(functionEndEscape, functionEnd) \
        .replace(functionEndEscapeEscape, functionEndEscape)


varKeywordP = re.compile(varKeyword)

def _escapeLocal(original):
    r"""
    >>> _escapeLocal('var ivar:uint = 0;\nvar varj:uint = cameras.length;')
    '& ivar:uint = 0;\n& varj:uint = cameras.length;'
    """
    original = _escapeWildCard(original)
    escaped = original.replace(varEscape, varEscapeEscape)
    return re.sub(varKeywordP, varEscape, escaped)


def _unescapeLocal(safe):
    """
    Preserve '&&'
    >>> _unescapeLocal(varEscapeEscape)
    '&'
    """
    return safe \
        .replace(varEscape, var) \
        .replace(varEscapeEscape, varEscape)


localVariableP = re.compile(localVariableEscaped)

def localVariables(funcContent):
    r"""
    >>> print localVariables('var i:uint = 0;;')
    var i = 0;;

    Remove data type from each local variable.
    >>> print localVariables('var ivar:uint = 0;\nvar varj:uint = cameras.length;')
    var ivar = 0;
    var varj = cameras.length;
    >>> print localVariables('f();\nvar ivar:uint = 0;\ng();')
    f();
    var ivar = 0;
    g();

    Wildcard type :*
    >>> print localVariables('var ivar = "wildcard";\nvar varj:uint = cameras.length;')
    var ivar= "wildcard";
    var varj = cameras.length;
    >>> print localVariables('var ivar:* = "wildcard";\nvar varj:uint = cameras.length;')
    var ivar= "wildcard";
    var varj = cameras.length;
    """
    escaped = _escapeLocal(funcContent)
    variables = localVariableP.findall(escaped)
    dataTypes = [dataType
        for keyword, declaration, dataType, definition in variables]
    parts = localVariableP.split(escaped)
    # print parts, dataTypes
    content = ''
    for part in parts:
        if part not in dataTypes:
            if part:
                content += part
    content = _unescapeLocal(content)
    return content


#                       private                     var    a       :  int

# http://revxatlarge.blogspot.com/2011/05/regular-expressions-excluding-strings.html
propP =  re.compile(commentPrefix
    + notStatic
    + namespace + '\s+' + localVariable, re.S)


def props(klassContent, inConstructor = False, klassName = ''):
    r"""As object members, indented by 4-spaces, with trailing comma.
    Undefined.
    >>> props('  public var ID:int;\n        public var exists:Boolean;')
    '    ID: undefined,\n    exists: undefined,'

    Defined.
    Auto-prepend class name to static.
    >>> props('private static const _ACTIVECOUNT;    public var ID:int = 1;\n    public var exists:Boolean = _ACTIVECOUNT;', klassName = 'FlxBasic')
    '    ID: 1,\n    exists: FlxBasic._ACTIVECOUNT,'

    Exclude static if exactly one space, because lookbehind only supports fixed-width
    >>> props('public var _ACTIVECOUNT:uint;')
    '    _ACTIVECOUNT: undefined,'
    >>> props('/** comment */\nstatic public var _ACTIVECOUNT:uint;')
    ''
    >>> props('public static var _ACTIVECOUNT:uint;')
    ''
    >>> props('static  public var _ACTIVECOUNT:uint;')
    '    _ACTIVECOUNT: undefined,'

    >>> print props('/** excluded */\nstatic public var _ACTIVECOUNT:uint;\n\n\n/** comment included */\npublic var x:int;')
        /** comment included */
        x: undefined,

    Exclude undefined, indented twice.
    >>> props('public var ID:int = 1;\npublic var exists:Boolean;',
    ...     inConstructor = True)
    '    ID = 1;'

    Preserve block comment, if not in constructor.
    >>> print props('/** active */\n\npublic var _ACTIVECOUNT:uint;')
        /** active */
    <BLANKLINE>
        _ACTIVECOUNT: undefined,
    """
    props = _parseProps(klassName, klassContent, propP)
    strs = []
    for comment, declaration, dataType, definition in props:
        if definition:
            if not inConstructor:
                definition = definition.replace(' =', ':').replace('=', ':')
            include = True
        else:
            definition = ': undefined'
            include = False
        line = ''
        if not inConstructor:
            if comment:
                line = comment
        line += declaration + definition
        if not inConstructor or include:
            strs.append(line)
    str = ''
    if inConstructor:
        separator = ';'
    else:
        separator = ','
    if strs:
        lineSeparator = separator + '\n'
        str = lineSeparator.join(strs)
        str = indent(str, 1)
        str += separator
    return str


def _formatComment(blockComment):
    if blockComment:
        blockComment = _unescapeEnds(blockComment)
        blockComment = indent(blockComment, 0)
        blockComment = blockComment.lstrip()
        blockComment += '\n'
    return blockComment


def _escapeWildCard(klassContent):
    """
    >>> _escapeWildCard('')
    ''
    >>> _escapeWildCard(':*')
    ''
    >>> _escapeWildCard(':Object')
    ':Object'
    """
    return klassContent.replace(':*', '')


def _parseProps(klassName, klassContent, funcP):
    escaped = _escapeEnds(klassContent)
    props = funcP.findall(escaped)
    formatted = []
    staticDeclarations = _findDeclarations(escaped, 
        [staticPropP, staticMethodP])
    for blockComment, name, dataType, definition in props:
        blockComment = _formatComment(blockComment)
        definition = _unescapeEnds(definition)
        definition = scopeMembers(staticDeclarations, definition, klassName)
        formatted.append([blockComment, name, dataType,
            definition])
    return formatted


def _parseFuncs(klassName, klassContent, funcP, instance = True):
    r"""
    Preserve '&&'
    >>> klassContent = 'public static function no(){return 0 && 1}'
    >>> funcs = _parseFuncs('Klass', klassContent, staticMethodP, False)
    >>> print funcs[0]['content']
        return 0 && 1

    Do not prefix static reference.
    >>> klassContent = 'public function Klass(){return Klass.NO}'
    >>> funcs = _parseFuncs('Klass', klassContent, methodP)
    >>> print funcs[0]['content']
        return Klass.NO

    Instance scope before static scope.
    >>> klassContent = 'public var score;\npublic static function score(){};\npublic function f(){return score;}'
    >>> funcs = _parseFuncs('Klass', klassContent, methodP)
    >>> print funcs[0]['content']
        return this.score;

    Static cannot refer to instance.
    >>> klassContent = 'public var score;\npublic static function score(){};\npublic static function f(){return score;}'
    >>> funcs = _parseFuncs('Klass', klassContent, staticMethodP, False)
    >>> print funcs[1]['content']
        return Klass.score;

    Do not prefix argument.
    >>> klassContent = 'public static var score;\npublic static function f(score="\\n"){return score;}'
    >>> funcs = _parseFuncs('Klass', klassContent, staticMethodP, False)
    >>> print funcs[0]['content']
    <BLANKLINE>
        if (undefined === score) {
            score="\n";
        }    return score;
    >>> print funcs[0]['argumentText']
    score
    """
    escaped = _escapeEnds(klassContent)
    funcs = funcP.findall(escaped)
    staticDeclarations = _findDeclarations(escaped, 
        [staticPropP, staticMethodP])
    if instance:
        instanceDeclarations = _findDeclarations(escaped, [
            propP, methodP], excludes = [klassName])
    formatted = []
    for blockComment, name, argumentAS, content in funcs:
        blockComment = _formatComment(blockComment)
        name = indent(name, 0)
        arguments = argumentP.findall(argumentAS)
        argumentsJS = []
        defaultArguments = []
        argumentDeclarations = []
        for declaration, dataType, definition in arguments:
            if declaration not in argumentDeclarations:
                argumentDeclarations.append(declaration)
            argumentsJS.append(declaration)
            if definition:
                defaultArguments.append('if (undefined === ' + declaration + ') {')
                defaultArguments.append(cfg.indent + declaration + definition + ';')
                defaultArguments.append('}')
        if instance:
            thisInstanceDeclarations = exclude(instanceDeclarations, argumentDeclarations)
        thisStaticDeclarations = exclude(staticDeclarations, argumentDeclarations)
        defaults = ''
        if instance:
            defaults = props(klassContent, True, klassName)
            if defaults:
                defaults = scopeMembers(thisInstanceDeclarations, defaults, 'this')
        argumentText = ', '.join(argumentsJS)
        defaultArgumentText = '\n'.join(defaultArguments)
        if defaultArgumentText:
            defaultArgumentText = '\n' + indent(defaultArgumentText, 1)
        if not content or content.isspace():
            content = ''
        else:
            content = localVariables(content)
            content = trace(content)
            content = superClass(content)
            content = catch(content)
            content = asType(content)
            content = intType(content)
            content = isInstanceOf(content)
        content = indent(content, 1)
        content = defaultArgumentText + content
        if instance:
            content = scopeMembers(thisInstanceDeclarations, content, 'this')
        content = scopeMembers(thisStaticDeclarations, content, klassName)
        formatted.append({'blockComment': blockComment, 
            'name': name, 
            'argumentText': argumentText, 
            'content': content, 
            'defaults': defaults, 
            'defaultArguments': defaultArguments})
    return formatted


def indent(text, indents=1):
    r"""Standardize indent to a number of indents.
    >>> print indent('             ab\n                 c', 1)
        ab
            c
    >>> print indent('             ab\n                 c', 2)
            ab
                c
    >>> print indent('                 ab\n                 c', 1)
        ab
        c
    >>> print indent('                 ab\n                 c', 0)
    ab
    c
    """
    text = textwrap.dedent(text.replace('\r\n', '\n'))
    lines = []
    for line in text.splitlines():
        if line:
            space = cfg.indent * indents
        else:
            space = ''
        lines.append(space + line)
    text = '\n'.join(lines)
    return text


def _formatFunc(func, operator):
    return func['blockComment'] + func['name'] + operator + 'function(' \
        + func['argumentText'] \
        + ')\n{' \
        + func['content'] + '\n}'


def _findDeclarations(klassContent, propPs, excludes = []):
    declarations = []
    for propP in propPs:
        props = propP.findall(klassContent)
        for comment, declaration, dataType, definition in props:
            if declaration not in excludes:
                if declaration not in declarations:
                    declarations.append(declaration)
    return declarations
    

superClassP = re.compile(r'(\s+)super\s*(\()')

def superClass(funcContent):
    r"""Does not support call to another function.
    >>> print superClass('var a; super(a);\nsuper.f(1)');
    var a; this._super(a);
    super.f(1)
    """
    return re.sub(superClassP, r'\1' + cfg.superClass + r'\2', funcContent)


traceP = re.compile(r'(\s+)trace\s*(\()')

def trace(funcContent):
    r"""
    >>> print trace('var a; trace(a);\ntrace(1)');
    var a; cc.log(a);
    cc.log(1)
    """
    return re.sub(traceP, r'\1' + cfg.log + r'\2', funcContent)


catchP = re.compile(r'(\bcatch\s*\()(\w+):[^\(]+\)')

def catch(funcContent):
    r"""
    >>> print catch('catch(err:Error)');
    catch(err)
    """
    return re.sub(catchP, r'\1\2)', funcContent)


asP = re.compile(r'\s+as\s+\w+\b')

def asType(funcContent):
    r"""Only simple, strict form of weak typecasting.
    >>> print asType('child as DisplayObjectContainer;');
    child;
    >>> print asType('child as DisplayObjectContainer');
    child

    Careful of comments.
    >>> print asType('/* This child as a display object. */');
    /* This child display object. */
    """
    return re.sub(asP, r'', funcContent)


isP = re.compile(r'\s+is\s+(\w+)\b')

def isInstanceOf(funcContent):
    r"""Only simple, strict form of is class.
    >>> print isInstanceOf('child is DisplayObjectContainer;');
    child instanceof DisplayObjectContainer;
    >>> print isInstanceOf('child is DisplayObjectContainer');
    child instanceof DisplayObjectContainer

    Careful of comments.
    >>> print isInstanceOf('/* This child is a display object. */');
    /* This child instanceof a display object. */
    """
    return re.sub(isP, r' instanceof \1', funcContent)


intTypeP = re.compile(r'([^\.\w])\bint\(')

def intType(funcContent):
    r"""Only simple, strict form of integer casting.
    >>> print intType('(int(a))');
    (Math.floor(a))
    >>> print intType(' int(a/-1.0 + 1)');
     Math.floor(a/-1.0 + 1)
    >>> print intType('A.int(a/-1.0 + 1)');
    A.int(a/-1.0 + 1)
    >>> print intType('int(a/-1.0 + 1)');
    int(a/-1.0 + 1)
    """
    return re.sub(intTypeP, r'\1Math.floor(', funcContent)


def _findLocalDeclarations(funcContent):
    escaped = _escapeLocal(funcContent)
    variables = localVariableP.findall(escaped)
    declarations = [declaration
        for keyword, declaration, dataType, definition in variables]
    return declarations


def exclude(list, exclusions):
    """New list
    >>> exclude(['a', 'b', 'c'], ['b'])
    ['a', 'c']
    """
    included = []
    for item in list:
        if not item in exclusions:
            included.append(item)
    return included


identifierP = re.compile(r'[^\w\."\']+\b(\w+)\b')

def scopeMembers(memberDeclarations, funcContent, scope):
    r"""
    >>> print scopeMembers(['x', 'y', 'f'], 'var x:int = 0;\nx += y;\nf();\nfunction g(){}; g()', 'this')
    var x:int = 0;
    x += this.y;
    this.f();
    function g(){}; g()

    Include comments.
    >>> print scopeMembers(['x', 'y', 'f'], 'var x:int = 0;\n//x += y;', 'FlxCamera')
    var x:int = 0;
    //x += FlxCamera.y;

    Include not space at start, such as parenthesis or division sign.
    >>> print scopeMembers(['x', 'y', 'f'], 'var x:int = 0;\nx += (y + 1)/y - FlxCamera.y;\ntrace("y "+y);', 'FlxCamera')
    var x:int = 0;
    x += (FlxCamera.y + 1)/FlxCamera.y - FlxCamera.y;
    trace("y "+FlxCamera.y);

    Careful replacement is unaware of quoted string context.
    >>> print scopeMembers(['end'], 'gotoAndPlay("end");\ntrace("The end");', 'View')
    gotoAndPlay("end");
    trace("The View.end");

    Careful replacement is unaware of quoted string context.
    >>> print scopeMembers(['STYLE_PLATFORMER'], 'case STYLE_PLATFORMER:\n{a: 1, STYLE_PLATFORMER: STYLE_PLATFORMER};', 'FlxCamera')
    case FlxCamera.STYLE_PLATFORMER:
    {a: 1, STYLE_PLATFORMER: FlxCamera.STYLE_PLATFORMER};
    """
    scoped = funcContent
    localDeclarations = _findLocalDeclarations(funcContent)
    memberDeclarations = exclude(memberDeclarations, localDeclarations)
    identifiers = identifierP.findall(funcContent)
    memberIdentifiers = []
    for identifier in identifiers:
        if identifier in memberDeclarations:
            if identifier not in memberIdentifiers:
                memberIdentifiers.append(identifier)
    for identifier in memberIdentifiers:
        memberIdentifierP = re.compile(r'([^\w\."\']+)\b(%s)\b(?!:)' % identifier)
        scoped = re.sub(memberIdentifierP, r'\1%s.\2' % scope, scoped)
        caseP = re.compile(r'(\bcase\s+)\b(%s\s*:)' % identifier)
        scoped = re.sub(caseP, r'\1%s.\2' % scope, scoped)
    return scoped


#                                                     override        private                     function    func    (int a    )      :    int    {         }  
methodP =  re.compile(functionPrefix
    + notStatic
    + namespace 
    + '\s+' + function, re.S)


def methods(klassName, klassContent):
    r"""
    Ignore member variables.
    >>> methods('FlxCamera', '/** var */\npublic var ID:int;')
    ''

    Escapes end comment character with tilde, which is not special to pattern.
    >>> re.compile(comment, re.S).findall('/** comment ~/** var ~')
    ['/** comment ~', '/** var ~']

    Arguments.  Convert default value.
    >>> print methods('FlxCamera', '/** comment */\npublic var ID:int;\n\n\n\n/* var ~ */\npublic function FlxCamera(X:int,Y:int,Width:int,Height:int,Zoom:Number=-1){\nx=X}')
        /* var ~ */
        ctor: function(X, Y, Width, Height, Zoom)
        {
            if (undefined === Zoom) {
                Zoom=-1;
            }
            x=X
        }

    Ignore static functions.
    >>> methods('FlxCamera', '/** var */\nstatic public function f(){}')
    ''

    Comma-separate.
    >>> print methods('FlxCamera', 'internal function f(){}internal function g(){}')
        f: function()
        {
        },
    <BLANKLINE>
        g: function()
        {
        }

    Local variables.
    >>> print methods('FlxCamera', 'internal function f(){\nvar i:uint=1;\ni++}')
        f: function()
        {
            var i=1;
            i++
        }

    Explicitly include defaults into constructor.
    >>> print methods('FlxCamera', '/** comment */\npublic var ID:int = 0;private var x:int;private var f:Function;/* var ~ */\npublic function FlxCamera(X:int,Y:int,Width:int,Height:int,Zoom:Number=0){\nx=X\nf()}')
        /* var ~ */
        ctor: function(X, Y, Width, Height, Zoom)
        {
            this.ID = 0;
            if (undefined === Zoom) {
                Zoom=0;
            }
            this.x=X
            this.f()
        }

    Reference to static property and function.
    >>> print methods('PrefixStatics', 'public static var ID:int = 0;\n\nstatic public function f(){}\npublic function method(){\nID=1\nf()}')
        method: function()
        {
            PrefixStatics.ID=1
            PrefixStatics.f()
        }
    """
    funcs = _parseFuncs(klassName, klassContent, methodP)
    functionNames = [func['name'] for func in funcs]
    strs = []
    for func in funcs:
        if klassName == func['name']:
            func['name'] = 'ctor'
            defaults = func['defaults']
            if defaults:
                func['content'] = '\n' + defaults + func['content']
        str = _formatFunc(func, ': ')
        str = indent(str, 1)
        strs.append(str)
    return ',\n\n'.join(strs)


staticMethodP =  re.compile(functionPrefix
    + staticNamespace
    + '\s+' + function, re.S)

def staticMethods(klassName, klassContent):
    r"""
    Ignore member variables.
    >>> staticMethods('FlxCamera', '/** var */\npublic static var ID:int;')
    ''

    Arguments.  Does not convert default value.
    >>> print staticMethods('FlxCamera', '/** comment */\npublic var x:int;\npublic static var x:int;\nprivate static function f(){}/* var ~ */\npublic static function create(X:int,Y:int,Width:int,Height:int,Zoom:Number=0):*{\nf();\nx=X}')
    FlxCamera.f = function()
    {
    };
    <BLANKLINE>
    /* var ~ */
    FlxCamera.create = function(X, Y, Width, Height, Zoom)
    {
        if (undefined === Zoom) {
            Zoom=0;
        }
        FlxCamera.f();
        FlxCamera.x=X
    };

    Ignore methods.
    >>> staticMethods('FlxCamera', '/** var */\npublic function f(){};')
    ''

    Multiple with 2 lines between.  Return type any.
    >>> print staticMethods('C', 'private static function f(){}private static function g():*{}')
    C.f = function()
    {
    };
    <BLANKLINE>
    C.g = function()
    {
    };

    Nested local function brackets.
    >>> print staticMethods('C', 'private static function f(){\nfunction g(){}}')
    C.f = function()
    {
        function g(){}
    };
    """ 
    funcs = _parseFuncs(klassName, klassContent, staticMethodP, False)
    functionNames = [func['name'] for func in funcs]
    strs = []
    for func in funcs:
        func['name'] = klassName + '.' + func['name']
        str = _formatFunc(func, ' = ') + ';'
        strs.append(str)
    return '\n\n'.join(strs)


requireP = re.compile(r'\s*\bimport\s+([\w\.]+)')

def requires(text):
    r"""Reformat import statement as node.js require.
    Replaces "." with "/".
    Replaces path from requireSubs.
    >>> print requires(' import flash.display.Bitmap;\nprivate var i:int;')
    /*jslint node: true */
    "use strict";
    <BLANKLINE>
    require("src/View/Bitmap.js");
    <BLANKLINE>
    <BLANKLINE>
    >>> print requires('public var j:uint;\n import flash.display.Bitmap;\nprivate var i:int;')
    /*jslint node: true */
    "use strict";
    <BLANKLINE>
    require("src/View/Bitmap.js");
    <BLANKLINE>
    <BLANKLINE>
    >>> print requires('public var j:uint;')
    "use strict";
    <BLANKLINE>
    """
    modules = requireP.findall(text)
    requiresText = ''
    if modules:
        requires = []
        for module in modules:
            mod = module.replace('.', '/') + '.js'
            for fromPath, toPath in cfg.requireSubs:
                mod = mod.replace(fromPath, toPath)
            req = 'require("%s");' % mod
            requires.append(req)
        requires.insert(0, '/*jslint node: true */\n"use strict";\n')
        requiresText = '\n'.join(requires) + '\n\n'
    else:
        requiresText = '"use strict";\n'
        pass
    return requiresText


#                     package   org.pkg   {       class   ClasA    extends   Clas{        }}
klassCommentP =  re.compile('package\s*[\w\.]*\s*{[\s\S]*?' 
    + commentPrefix
    + namespace + '?\s*' + '(?:\s+final\s+)?'
    + 'class\s+\w+', re.S)

klassP =  re.compile('package\s*[\w\.]*\s*{[\s\S]*' 
    + 'class\s+(\w+)' 
    + '(?:\s+extends\s+\w+\s*)?\s*{([\s\S]*)}\s*}', re.S)

def findClassAndContent(text):
    r"""Return (blockComment, name, content)
    >>> findClassAndContent('package{\nclass Newline\n{}\n}')
    ['', 'Newline', '']

    Line comment not preserved.
    >>> findClassAndContent('package{class Oneline{}}')
    ['', 'Oneline', '']

    Line comment not preserved.
    >>> findClassAndContent('package{// line\nclass LineComment{}}')
    ['', 'LineComment', '']

    Block comment preserved.
    >>> findClassAndContent('package{/*comment*/public final class BlockComment{}}')
    ['/*comment*/', 'BlockComment', '']
    """
    escaped = _escapeEnds(text)
    # print escaped
    comments = klassCommentP.findall(escaped)
    nameContents = klassP.findall(text)
    if nameContents:
        commentNameContents = []
        if comments and comments[0]:
            comments[0] = _unescapeEnds(comments[0])
            commentNameContents.append(comments[0])
        else:
            commentNameContents.append('')
        commentNameContents.append(nameContents[0][0])
        commentNameContents.append(nameContents[0][1])
        return commentNameContents

def convertVector(text):
    """
    >>> convertVector('var v:Vector.<A> = new <A>[new A()]')
    'var v:Array = [new A()]'
    >>> convertVector('var aVector:Vector.<int> = new Vector.<int>(3)')
    'var aVector:Array = new Array()'
    >>> convertVector('var aVector:Vector.<Vector.<int>> = new Vector.<Vector.<int>>(2)')
    'var aVector:Array = new Array()'
    """
    text = re.sub(vectorConstructorP, arrayConstructor, text)
    text = re.sub(vectorTypeP, arrayType, text)
    text = re.sub(vectorLiteralP, '', text)
    return text

def convert(text):
    text = convertVector(text)
    klassComment, klassName, klassContent = findClassAndContent(text)

    str = '';
    str += requires(text)
    if klassComment:
        str += indent(klassComment, 0) + '\n'
    str += 'var ' + klassName + ' = ' + cfg.baseClass + '.extend(\n{' 
    str += '\n' + props(klassContent, False, klassName) 
    str += '\n\n' + methods(klassName, klassContent)
    str += '\n});'
    str += '\n\n' + staticProps(klassName, klassContent)
    str += '\n\n' + staticMethods(klassName, klassContent)
    return str


def convertFile(asPath, jsPath):
    text = codecs.open(asPath, 'r', 'utf-8').read()
    str = convert(text)
    f = codecs.open(jsPath, 'w', 'utf-8')
    # print(str)
    f.write(str)
    f.close()   


def convertFiles(asPaths):
    for asPath in asPaths:
        root, ext = os.path.splitext(asPath)
        jsPath = root + '.js'
        convertFile(asPath, jsPath)

def realpath(path):
    """
    http://stackoverflow.com/questions/4934806/python-how-to-find-scripts-directory
    """
    return os.path.join(os.path.dirname(os.path.realpath(__file__)), path)


def _testCfg():
    """Overrides cfg, so perform this after all operations.
    Tests expect indent 4-spaces.
    """
    cfg.indent = '    '
    cfg.log = 'cc.log'
    cfg.requireSubs = [['flash/display', 'src/View']]
    cfg.superClass = 'this._super'
    import doctest
    doctest.testmod()
    import glob
    convertFiles(glob.glob(realpath('test/*.as')))


if '__main__' == __name__:
    import sys
    if len(sys.argv) <= 1:
        print __doc__
    if 2 <= len(sys.argv) and '--test' != sys.argv[1]:
        convertFiles(sys.argv[1:])
    _testCfg()
