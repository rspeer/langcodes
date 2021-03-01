## Langcodes and type annotations

_(a lament about the state of a Python feature in 2021)_

Python's type annotations can be a nice way to clearly establish what the
inputs and outputs of a function are.

From its original release in 2014, `langcodes` has contained type annotations.
At first, annotating functions with types was a best-effort, improvisational thing
without well-defined rules.

When type annotations became common enough, Python introduced the theory of
"gradual typing", establishing conventions about what the type annotations
meant. At this point, it became important to verify that the types were actually
providing correct information.

langcodes' types used to be tested with `obiwan`, a tool that instrumented tests
at runtime to check that parameters and return values had the correct types.

Later, Python's core developers endorsed `mypy`, a static type checker.
Gradually, the type notation used by `mypy` -- which is different from `obiwan`
-- has become part of the Python language itself. `mypy` won. `obiwan` lost,
and it stopped being developed in 2015.

Here's what we've lost by settling on `mypy`: there is no _testing procedure_
for type annotations anymore, as far as I know. I've asked around.

What I mean is, you can verify that your Python code passes its unit tests by
running `pytest` and getting no errors. There's no equivalent procedure for types.

There's only the static type checker.

If your decision procedure is "running `mypy` on the project directory gives no
errors", please understand that I've never seen _any_ nontrivial code that meets
that standard. That doesn't fit with the idea of "gradual typing" at all.
Instead, it requires all of the code, and all of its dependencies, to have type
annotations that are thorough enough to be statically verified by `mypy`.

I think the standard that people actually want type annotations to meet is: "my
IDE shows helpful things about types, and doesn't complain about type errors,
when I use this library correctly". And that just sounds impossible to test at
the moment.

So here's my request, if you want to raise an issue about types:

- Make sure that what you're asking for works for others as well. It shouldn't
  just be specific to your IDE or your environment, and it shouldn't require
  ugly workarounds on still-supported versions of Python.

- Please understand that I didn't vote for `mypy` (not that there was a vote,
  but, y'know, metaphorically) and there's a limit to the amount of work I'll
  do to make it happy.

- Give me some way to verify that what you're asking for would be more correct
  than what was there before.
