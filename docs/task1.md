---
layout: page
title: Task 1
---

# Task 1: Classification

## Description

The input to the system is a music audio file. The output is the set of instruments that are played anywhere in the input file. Such systems can be used to create instrument-related tags, which can serve as features for high level systems such as recommenders. 

## Format

[TBD]

## Evaluation

[TBD]

In the following, let $X=\\{x_1,\dots,x_n\\}$ be the set of instruments annotated for the input audio file, and let $Y=\\{y_1,\dots,y_m\\}$ be the set of instruments predicted by the system for that same audio file. In addition, let $1[e]$ be an indicator function that evaluates to $1$ if $e$ is true and $0$ otherwise.

### Hierarchy-unaware Measures

The following measures are defined ignoring the hierarchy of classes:

- **Precision** evaluates the ability of the system to identify instruments without making mistakes (avoid false positives). It computes the fraction of predictions that are correct:

$$P=\frac{1}{m}\sum_{y\in Y}{1[y\in X]}$$

- **Recall** evaluates the ability of the system to identify all instruments present in the input file (avoid false negatives). It computes the fraction of annotations correctly predicted:

$$R=\frac{1}{n}\sum_{x\in X}{1[x\in Y]}$$

- **F-measure** integrates both Precision and Recall in a single score:

$$F=2\frac{P\cdot R}{P+R}$$

### Hierarchy-aware Measures

We will use the hierarchical counterparts of $P$, $R$ and $F$ defined by Kiritchenko et al. Let $anc(x)$ be a function that returns the set of ancestors of class $x$, excluding the root of the hierarchy. The extended set of reference annotations is thus $X^\*=\cup_{x\in X}{anc(x)}$, while the extended set of predictions is similarly $Y^\*=\cup_{y\in Y}{anc(y)}$. The above measures can now be reformulated as follows to account for the hierarchy:

- **hPrecision:**

$$hP=\frac{1}{|Y^*|}\sum_{y^*\in Y^*}{1[y^*\in X^*]}$$

- **hRecall:**

$$hR=\frac{1}{|X^*|}\sum_{x^*\in X^*}{1[x^*\in Y^*]}$$

- **hF-measure:**

$$hF=2\frac{hP\cdot hR}{hP+hR}$$
