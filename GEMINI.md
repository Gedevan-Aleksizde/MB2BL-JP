# Main GEMINI.md

## General Rules

You MUST NOT request me the permission for execusion except for the following rules.

* You can use uv and .venv. Don't use other Python envionment and break the existing environment.
* You never change git commit history; you must not use git commit, git push, git pull, git merge, and so on.
* You MUST NOT change any other non-target files.

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
