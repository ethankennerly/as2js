as2js
=====

Reformat ActionScript 3 class files to JavaScript.

Forked from 06\_jw as2js by Ethan Kennerly.


Usage
=====

* Manually conform ActionScript to JavaScript by each item in not supported.

* Reformat:

    python as2js.py file.as

* Manually conform JavaScript requires and libraries.


Features
========

 * Static functions.

 * Windows or Unix line endings.

 * Print text.

 * Declared, undefined variable.

 * Either order of declaring static.

 * Declare member variables.

 * Extend class idiom.

 * Methods in extend idiom.

 * Static methods.

 * Specify multiple files.

 * Configuration class to extend.

 * Remove data type from each local variable.

 * Nested brackets.

 * Dedent methods.

 * Default arguments.

 * Constants.

 * Constructor member variable reassignment.

 * Reformat import statement as node.js require.

 * Auto prefix member access with this.

 * Auto prefix static access with class name.

 * Reformat AS3 to untyped, explicit scope to test.

 * Trace statement to a log message.

 * Reformat super to this.\_super.

 * Preserve class comment.

 * Preserve variable comment.

 * Configure substitute require paths.

 * Override default configurations.

 * Remove data type from Try/catch.

 * Simple type casting with "as" operator.  
 
 * Simple pattern of "is" into "instanceof".

Not supported
=============

Vim commands are listed for some of these manual translations.


 * Scoping is unaware of quoted string context.

 * Multiple variables assigned with a comma.

    :lvimgrep / var [^;]*, [^;]*:[A-Za-z\*]/ *.as

 * Extending a base class other than the configuration baseClass.

    :lvimgrep / extends / *.as

 * Reformat super call to another function to this.\_super.

    :lvimgrep /\<super\>/ *.as

 * Typecasting with MyType(variable) syntax.  Replace with "instanceof".

    :lvimgrep / int(/ *.as

 * Preserve line comment before a member variable or function.

    :lvimgrep /^        \/\/ / *.as

 * Integer constants, such as "int.MIN\_VALUE"

    :lvimgrep /\<int\./ *.as

 * Auto prefix private variables with underscore.

    :args *.as
    :argdo %s/private var /private var _/gIce

 * Apply Math.floor to float converted to an int or uint.  Such as during random index.

    :args *.as
    :argdo %s/\(:int = \)\([^;]*random[^;]*;\)/\1Math.floor(\2)/gIce | update

 * Comments or parentheses in function arguments or variable definitions.

 * Vim in-place:  Read text from standard input and return text for use in vim 

    :%!python -m as2js/as2js.py

 * Variable or method with undeclared namespace.

    :lvimgrep /^        var / *.as
    :lvimgrep /^        function / *.as

 * Translate for each.  Example:  "for each(a in b){...}" into "for (var i = 0; i < b.length; i++) { var a = b[i]; ...}

    :lvimgrep /\<for each\>/ *.as

 * Include comment on return type and parameter type.

    :lvimgrep / function/ *.as

 * ActionScript 'get' and 'set' functions.

    :lvimgrep / function [gs]et / *.as

 * Require classes in same folder as this class.  Can explicitly include import.

    :lvimgrep /MyClass/ *.as

 * Does not tolerate missing semicolon after a variable definition.

    :lvimgrep / var .*[^;]$/ *.as

 * Classes without constructors.
 
 * Multiple classes per file.

 * Classes without functions.

 * Nonalphanumeric variable and function characters like '$'.

    :lvimgrep /\$/ *.js

 * Static is defined first in ActionScript but last in this idiom of JavaScript.  So default assignments won't be found.

 * Globals.

 * References to classes created by Flash Professional.  ActionScript compiler needs the literal class to avoid pruning.  These class references could be quoted, for example:

    :'a,'zs/\([A-Za-z0-9]\+\)/"\1"/g

 * Preprocessor directives such as "include".

    :argdo /\#include 

 * Anything else not mentioned in features above.
