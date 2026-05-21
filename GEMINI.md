# Main GEMINI.md

## General Rules

You MUST NOT request me the permission for execusion except for the following rules.

* You can use `uv` command. Don't use other Python envionment and break the existing environment.
* You never change git commit history; you must not use git commit, git push, git pull, git merge, and so on.
* You can use files and create new files to execute your task only in @AI/tools/ folder. You can create and edit files without permission if you do that in this folder.
* You MUST NOT change any other non-target files.
* Don't start to read and translate target file without permission to save to waste tokens.


Don't use any slang, jargon, or any other ambiguous wording. Explain your work accurately.

## definition of translating PO files 

You should follow the terminology listed in the following csv. The text column is correct terminology and text_EN column is the original words.

@AI/terminology.csv

Follow the following policies in the tlanslation-policy.md.

@AI/translation-policy.md

when I request to translate files, refering the other context files and use terminologies, and imitate the tones. 

You always forgot to specify the text encoding. Why? You must use UTF-8 encoding when loading PO files.

Don't remove fuzzy flags because I need confirm your translation later.

Note that you should change ONLY and ALL msgstr entries. DON'T CHANGE ANY OTHER PARTS and DON'T FORGET TO TRANSLATE ANY MSGSTR TO BE TRANSLATED.

You have failed the translation many times. Be MUCH MORE CAREFUL that you translate and validate the target text.

You have reported falsely again and again. After translation, You should verify that you does not violate the translation policies.

You don't have to change any entry without the fuzzy flag. It's already translated.

You MUST NOT change any entry without the fuzzy flag. It's already translated. How many times do I need to tell you this to make sure you understand?

Don't wrapping the text. All field should be in 1 line to git-friendly formatting. 