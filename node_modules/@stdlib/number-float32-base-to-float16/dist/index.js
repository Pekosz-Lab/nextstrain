"use strict";var v=function(e,i){return function(){return i||e((i={exports:{}}).exports,i),i.exports}};var q=v(function(_,s){
var T=typeof Math.f16round=="function"?Math.f16round:null;s.exports=T
});var F=v(function(b,E){
var l=require('@stdlib/math-base-assert-is-nanf/dist'),r=require('@stdlib/number-float64-base-to-float32/dist'),d=require('@stdlib/math-base-assert-is-finitef/dist'),n=require('@stdlib/constants-float16-eps/dist'),I=require('@stdlib/constants-float16-max/dist'),f=require('@stdlib/constants-float16-smallest-normal/dist'),p=require('@stdlib/constants-float32-eps/dist'),L=require('@stdlib/constants-float32-pinf/dist'),O=require('@stdlib/math-base-special-absf/dist'),c=r(1/p);function A(e){return r(r(e+c)-c)}function M(e){var i,u,t,a;return e=r(e),e===0||l(e)||!d(e)?e:(e<0?a=r(-1):a=r(1),u=O(e),u<f?r(r(r(a*A(r(r(u/f)/n)))*f)*n):(t=r(r(1+r(n/p))*u),i=r(t-r(t-u)),i>I||l(i)?r(a*L):r(a*i)))}E.exports=M
});var N=q(),P=F(),o;typeof N=="function"?o=N:o=P;module.exports=o;
/** @license Apache-2.0 */
//# sourceMappingURL=index.js.map
