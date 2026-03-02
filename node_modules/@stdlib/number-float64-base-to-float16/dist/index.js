"use strict";var s=function(r,e){return function(){return e||r((e={exports:{}}).exports,e),e.exports}};var f=s(function(P,v){
var E=typeof Math.f16round=="function"?Math.f16round:null;v.exports=E
});var c=s(function(S,q){
var F=require('@stdlib/math-base-assert-is-finite/dist'),a=require('@stdlib/constants-float16-eps/dist'),T=require('@stdlib/constants-float16-max/dist'),n=require('@stdlib/constants-float16-smallest-normal/dist'),N=require('@stdlib/constants-float64-eps/dist'),d=require('@stdlib/constants-float64-pinf/dist'),I=require('@stdlib/math-base-special-abs/dist'),l=1/N;function L(r){return r+l-l}function O(r){var e,i,t,u;return r===0||isNaN(r)||!F(r)?r:(r<0?u=-1:u=1,i=I(r),i<n?u*L(i/n/a)*n*a:(t=(1+a/N)*i,e=t-(t-i),e>T||isNaN(e)?u*d:u*e))}q.exports=O
});var p=f(),A=c(),o;typeof p=="function"?o=p:o=A;module.exports=o;
/** @license Apache-2.0 */
//# sourceMappingURL=index.js.map
