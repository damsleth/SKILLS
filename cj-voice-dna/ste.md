# tech_doc: Simplified Technical English and klarspråk

Rules for the `tech_doc` register. Voice is `off`: the text is precise and impersonal, and a reader who skims it can act on it.

## English: ASD-STE100 writing rules

ASD-STE100 is a controlled language with two parts: writing rules and a dictionary of approved words. The dictionary is copyrighted and not bundled here. Apply the writing rules fully. For vocabulary, use the most common word with its most common meaning. If the user has a licensed STE dictionary, check the text against it and say so. Without one, say the text follows the STE writing rules and has not been checked against the dictionary.

**Words**
- One word, one meaning. One meaning, one word. Pick a term and use it every time.
- Technical names (parts, commands, UI labels, file names) are allowed as they are. Put code identifiers in inline code.
- Noun clusters: 3 words at most. Break longer ones with a preposition ("the configuration file of the server").
- Use verbs as verbs. Write "examine the log", avoid "carry out an examination of the log".
- Use articles and demonstratives ("the", "a", "this") where the sentence allows.

**Procedures**
- 20 words at most per sentence.
- One instruction per sentence. Two actions in one sentence only when they happen at the same time.
- Imperative form: "Open the file.", "Run the command."
- Write the condition first: "If the build fails, examine the log."
- Numbered steps, one action per step. Put the result of a step, when the reader needs it, in its own sentence after the action.

**Descriptions**
- 25 words at most per sentence.
- One topic per paragraph, 6 sentences at most.
- Start with the most important information.

**Verbs and voice**
- Active voice. Say who or what does the action.
- Simple tenses: present, past, future.
- Use the -ing form only in technical names.

**Warnings and cautions**
- Start with a clear command ("Disconnect the power before you remove the cover.").
- Then give the risk in one short sentence.
- Keep notes for information. Instructions go in steps.

## Norwegian: klarspråk with transferable STE rules

STE exists only in English. For Norwegian technical text, use Språkrådet's klarspråk principles plus the STE rules that carry over:

- Most important first. The reader knows after one sentence what the text lets them do.
- Short sentences: 20 words at most in procedures, 25 in descriptions.
- One instruction per sentence, in imperative form ("Åpne fila.", "Kjør kommandoen.").
- Condition first: "Hvis bygget feiler, les loggen."
- Active form with a clear subject. Prefer "skriptet sletter fila" to "fila blir slettet".
- Verbs as verbs. Write "undersøk loggen", avoid "foreta en undersøkelse av loggen".
- One term per concept, the same term every time. Explain a technical term the first time, or link to it.
- Keep established English tech terms (`deploy`, `branch`, `pipeline`) as they are. Consistency beats translation.

## Self-check for tech_doc

1. Count the words in every sentence: over 20 in a procedure or 25 in a description, split it.
2. Every step holds one action in imperative form.
3. Every condition comes before its action.
4. Every concept uses one term throughout. List the terms and check for synonyms.
5. Passive sentences: rewrite them with a subject, unless the actor is unknown.
6. Humor, asides, opinions and rhetorical questions: remove them.
