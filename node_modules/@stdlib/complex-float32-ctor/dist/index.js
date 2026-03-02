"use strict";var o=function(r,e){return function(){return e||r((e={exports:{}}).exports,e),e.exports}};var s=o(function(S,n){"use strict";function c(){var r=""+this.re;return this.im<0?r+=" - "+-this.im:r+=" + "+this.im,r+="i",r}n.exports=c});var a=o(function(T,u){"use strict";function y(){var r={};return r.type="Complex64",r.re=this.re,r.im=this.im,r}u.exports=y});var E=o(function(d,v){"use strict";var m=require("@stdlib/assert-is-number").isPrimitive,p=require("@stdlib/utils-define-read-only-property"),i=require("@stdlib/utils-define-nonenumerable-read-only-property"),h=require("@stdlib/number-float64-base-to-float32"),l=require("@stdlib/string-format"),f=s(),w=a();function t(r,e){if(!(this instanceof t))throw new TypeError("invalid invocation. Constructor must be called with the `new` keyword.");if(!m(r))throw new TypeError(l("invalid argument. Real component must be a number. Value: `%s`.",r));if(!m(e))throw new TypeError(l("invalid argument. Imaginary component must be a number. Value: `%s`.",e));return p(this,"re",h(r)),p(this,"im",h(e)),this}i(t,"name","Complex64");i(t,"BYTES_PER_ELEMENT",4);i(t.prototype,"BYTES_PER_ELEMENT",4);i(t.prototype,"byteLength",8);i(t.prototype,"toString",f);i(t.prototype,"toJSON",w);v.exports=t});var b=E();module.exports=b;
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
