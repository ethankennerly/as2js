"use strict";
var TestVector = cc.Class.extend(
{
    words_commented_out: ["default"],
    words: ["default"],
    table: new Array(),

    setWords: function(nextWords)
    {
        this.words = nextWords;
    },

    getWords: function()
    {
        return this.words;
    }
});



