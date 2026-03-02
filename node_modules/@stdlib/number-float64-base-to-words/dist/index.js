"use strict";var i=function(e,r){return function(){return r||e((r={exports:{}}).exports,r),r.exports}};var c=i(function(T,v){"use strict";var f=require("@stdlib/assert-is-little-endian"),u,a,s;f===!0?(a=1,s=0):(a=0,s=1);u={HIGH:a,LOW:s};v.exports=u});var t=i(function(U,W){"use strict";var l=require("@stdlib/array-uint32"),p=require("@stdlib/array-float64"),q=c(),H=new p(1),o=new l(H.buffer),x=q.HIGH,G=q.LOW;function y(e,r,O,n){return H[0]=e,r[n]=o[x],r[n+O]=o[G],r}W.exports=y});var d=i(function(V,I){"use strict";var A=t();function E(e){return A(e,[0,0],1,0)}I.exports=E});var g=require("@stdlib/utils-define-nonenumerable-read-only-property"),L=d(),w=t();g(L,"assign",w);module.exports=L;
/**
* @license Apache-2.0
*
* Copyright (c) 2018 The Stdlib Authors.
*
* Licensed under the Apache License, Version 2.0 (the "License");
* you may not use this file except in compliance with the License.
* You may obtain a copy of the License at
*
*    http://www.apache.org/licenses/LICENSE-2.0
*
* Unless required by applicable law or agreed to in writing, software
* distributed under the License is distributed on an "AS IS" BASIS,
* WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
* See the License for the specific language governing permissions and
* limitations under the License.
*/
//# sourceMappingURL=index.js.map
