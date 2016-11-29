---
layout: page
title: Task 2
---

# Task 2: Retrieval

The input is a query instrument and a corpus of audio music files. The output is a list of at most 100 files from the corpus where the query instrument is played. Such systems can be used for instance by amateur players who want to practice some particular instrument.

## Format

[TBD]

## Evaluation

[TBD]

In the following, let $q$ be the query instrument, let $X=\\{x_1,\dots,x_n\\}$ be the set of excerpts annotated as containing the query instrument, and let $Y=\langle y_1,\dots,y_m \rangle$ be the list of excerpts retrieved by the system.

### Hierarchy-unaware Measures

- **Reciprocal Rank** evaluates the (inverse of the) effort required from the user to find the first relevant excerpt retrieved:

$$RR=\frac{1}{\min_{i}{\{i : y_i\in X\}}}$$

- **Precision at k** evaluates the ability of the system to retrieve relevant excerpts among the top $k$ retrieved:

$$P@k=\frac{1}{k}\sum_{i=1}^k{1[y_i\in X]}$$

We will evaluate with cutoffs k=5,10,15,20,50,100.

- **Average Precision** evaluates the ability of the system to retrieve all relevant excerpts and at the top of the results list:

$$AP=\frac{1}{|X|}\sum_{i=1}^m{1[y_i\in X]\cdot P@i}$$

### Hierarchy-aware Measures

ERR, EP@k and GAP
