---
layout: page
title: Task 2
---

# Task 2: Retrieval

In this task we consider a user with a corpus of audio music files, who wants a system to retrieve the files in which a certain instrument is played. This is the case for instance of amateur players who want to practice some particular instrument.

## Format

The input to the system is a query instrument from the taxonomy and a corpus of audio music files. The output is a list of at most $M=1000$ files deemed relevant to the query instrument.

[JAMS example]

## Evaluation

Several evaluation measures will be used to score a system output for a query instrument, all assuming that the user will start looking at the results from the top of the list.
Let $q$ be the query instrument, let $B(q)=\langle b_1,\dots,b_m \rangle$ be the list of excerpts retrieved by the system for that instrument, and let $A(b)=\\{a_1,\dots,a_n \\}$ be the set of instruments annotated for excerpt $b$. 
In addition, let $1[x]$ be an indicator function that evaluates to $1$ if $x$ is true and $0$ otherwise.

### Flat Measures

Several measures will be used to score a system output for a query instrument, ignoring the instrument taxonomy. This means that an excerpt $b$ will be considered relevant for instrument $q$ only if $q \in A(b)$:

- **Reciprocal Rank** evaluates the (inverse of the) effort required from the user to find the first relevant excerpt retrieved:

  $$RR=\frac{1}{ \min{\{i~:~q \in A(b_i)\}} }.$$

- **Precision at k** evaluates the ability of the system to retrieve relevant excerpts among the top $k$ retrieved:

  $$P@k=\frac{1}{k} \sum_{i=1}^k{ 1[q \in A(b_i)] }.$$

  We will evaluate with cutoffs $k=5,10,15,20,50,100$.

- **Average Precision** evaluates the ability of the system to retrieve all relevant excerpts and at the top of the results list:

  $$AP=\frac{1}{n} \sum_i{ 1[q \in A(b_i)]\cdot P@i }.$$

For each measure, systems will be ranked by their mean score over all instruments in the taxonomy.

### Hierarchical Measures

We will also use a hierarchical version of $RR$ following the principles of Chapelle et al., and versions of $P@k$ and $AP$ following the principles of Robertson et al. For illustration purposes, assume the instrument class taxonomy in the figure, and assume the query instrument $q=G$.

<p style="text-align:center"><img src ="img/sample_taxonomy.png" /></p>

Intuitively, an instrument $a$ will be relevant for the query $q$ to the extent that they are close to each other in the hierarchy. Because our taxonomy has two levels, we define the instrument relevance as

$$r(a,q) = \begin{cases}2 & a = q \\
  1 & a~\text{and}~q~\text{are siblings} \\
  0 & \text{otherwise} \end{cases}.$$

The excerpt relevance of the $i$-th retrieved file is then the highest such relevance for each of its reference annotations: $r_i=\max_{a \in A(b_i)}{ r(a,q) }$. The following measures will be used to score a system output for a query instrument, accounting for the instrument taxonomy:

- **Expected Recriprocal Rank** is defined as the expected $RR$ considering that a user stops looking at the returned excerpts at some point. Let $p_i$ be the probability that the user finds excerpt $b_i$ satisfactory. The probability that she stops at that point is therefore $p_i \prod_{j=1}^{i-1}{(1-p_j)}$. The expected reciprocal rank is thus:

  $$ERR=\sum_i{\frac{1}{i} p_i \sum_{j=1}^{i-1}{(1-p_j)} }.$$

  With our two-level taxonomy, we will define the probability of satisfaction as $p_i=r_i/2$.

- **Expected Precision at k** is defined as the expected $P@k$ over a population of users with different thresholds to consider instrumet $a$ relevant for query instrument $q$. In the example, a restrictive user would only consider instrument $G$ as relevant, while a less restrictive user could also consider its siblings $E$ and $F$. A user with threshold $t$ will consider as relevant any instrument $a$ such that $r(a,q)\geq t$. The binary $P@k$ with threshold $t$ is thus $P@k_t=\frac{1}{k}\sum_{i=1}^k{ 1\[r_i \geq t\] }$. Let $p_t$ be the probability that a user implicitly uses threshold $t$, such that $p_0=0$ and $\sum{p_t}=1$. The expected precision at $k$ over the population of users is therefore:

  $$EP@k=\sum_t{ p_t \cdot P@k_t }.$$

  With our two-level taxonomy, we will use the distribution of thresholds $p_1=1/3$, $p_2=2/3$.

- **Graded Average Precision** is defined similarly, taking into account that an excerpt with relevance $r_i$ only contributes to the binary precisions of levels $\\{1, \dots, r_i\\}$:

$$GAP=\frac{ \sum_i \sum_{t=1}^{r_i}{ p_t \cdot P@i_t} }{ \sum_i \sum_{t=1}^{r_i}{p_t} }.$$

For each measure, systems will be ranked by their mean score over all instruments in the taxonomy.

## References

- O. Chapelle, D. Metzler, Y. Zhang and P. Grinspan (2009). [Expected Reciprocal Rank for Graded Relevance](http://olivier.chapelle.cc/pub/err.pdf). *ACM International Conference on Information and Knowledge Management*.
- S. Robertson, E. Kanoulas and E. Yilmaz (2010). [Extending Average Precision to Graded Relevance Judgments](http://www.ccs.neu.edu/home/ekanou/research/papers/mypapers/sigir10a.pdf). *International ACM SIGIR Conference on Research and Development in Information Retrieval*.
