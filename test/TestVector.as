package com.finegamedesign.tests
{
    public class TestVector
    {
        // In comment:  private var words_commented_out:Vector.<String> = new <String>["default"];
        private var words:Vector.<String> = new <String>["default"];
        private var table:Vector.<Vector.<int>> = new Vector.<Vector.<int>>(4);

        public function setWords(nextWords:Vector.<String>):void
        {
            words = nextWords;
        }

        public function getWords():Vector.<String>
        {
            return words;
        }
    }
}
