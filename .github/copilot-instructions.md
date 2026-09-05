---
applyTo: "**"
---


# AI Coding Agent Standards

## Code Generation
- Only generate code that is directly usable and relevant to the user's real-world scenario.
- Do not add, change, or remove any logic or behavior except what is explicitly requested by the user.
- If you have suggestions for improvements, present them to the user for approval before implementation.
- Ensure all generated code is syntactically correct and executable unless the user requests conceptual examples.
- When modifying code, use the diff tool and specify the exact location for insertion, update, or removal; never output the entire file.
- Show only the minimal changes required; do not repeat existing code.
- Exclude unnecessary boilerplate, placeholder code, or unrelated code unless explicitly requested.
- Reference only files, functions, or classes that exist in the current workspace; do not invent or hallucinate project structure.
- For external dependencies, use correct integration and document installation steps outside the code.
- If refactoring is requested without a code or file reference, inform the user and do not generate code.
- When refactoring, restrict changes strictly to the scope specified by the user; do not alter unrelated code or logic.

When the user requests code improvement, provide a clear description for each change and the reason for its inclusion, removal, or modification. If an improvement conflicts with a user instruction, explain why the change is necessary.
When the user requests code optimization, explain each optimization and the rationale for the change. If logic is added or removed to benefit optimization, provide a detailed explanation for the change and its necessity.

## Naming & Structure
- Use clear, descriptive, and consistent names for functions and variables, following best practices for the language in use.
- Apply established naming conventions (PascalCase, camelCase, ALL_CAPS) as appropriate for the language and context.
- Organize code into logical, modular units; group related functionality and avoid monolithic structures.
- Limit code nesting to a maximum of two levels for conditions, loops, and other control flows; refactor nested logic into separate functions or logic blocks.
- Avoid chaining more than two conditional existence checks in a single logic block unless strictly necessary.
- Do not use else clauses in if statements; prefer early returns to simplify logic and prevent unnecessary evaluation.

## Design Patterns & Best Practices
- Apply the most suitable design pattern for the problem; if no standard pattern is used, suggest one to the user before generating code.
- Avoid ambiguous instructions and outputs; be explicit and precise in all code and explanations.
- Always follow the user's stated preferences and requirements in every response.

## Error Handling
- Handle errors only when strictly necessary for the logic; do not use try/catch blocks for normal control flow or to mask issues.

## Security & Compatibility
- Prioritize secure and performant code; avoid anti-patterns and unsafe practices.
- Do not use deprecated language features, libraries, or APIs.

## Documentation & Comments
- Do not generate docstrings or documentation unless explicitly requested by the user.
- Do not generate comments in code under any circumstances, including inline, block, or explanatory comments. Do not remove or modify any existing comments.

## Output & Communication
- Do not use pleasantries or conversational language; responses must be strictly technical and direct.
- Adapt explanations to the user's experience level; keep explanations concise and only as detailed as needed for the user's demonstrated experience or difficulty.