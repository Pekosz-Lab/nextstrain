binomial.js is a simple module for creating binomial coefficients.  It includes memoization by default.  

Usage with memoization:

var n_choose_k = binomial.get(n, k);


Usage without memoization:

var n_choose_k = binomial.get_no_memo(n, k);