# Instruction Set Architecture Files #

In this directory, all `.isa` files must be placed. These files contain every assembly keyword mnemonic of the processor for which the compaction is performed.

The syntax of an `.isa` file is the following in a somewhat BNF format

```
line         ::= word \n
              |  comment_line \n
comment_line ::= # comment
comment      ::= <any_character> comment
word         ::= <any_character_except_whitespace>
```

- `any_character` is whichever character and 
- `any_character_except_whitespace` expects a **single** sequence of characters.

All lines beginning with `#` are ignored and each line must have exactly one word i.e., the assembly mnemonic of the respective ISA.
