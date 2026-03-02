"use strict";var o=function(e,r){return function(){return r||e((r={exports:{}}).exports,r),r.exports}};var s=o(function(S,n){"use strict";function c(){var e=""+this.re;return this.im<0?e+=" - "+-this.im:e+=" + "+this.im,e+="i",e}n.exports=c});var a=o(function(d,u){"use strict";function l(){var e={};return e.type="Complex128",e.re=this.re,e.im=this.im,e}u.exports=l});var E=o(function(q,v){"use strict";var m=require("@stdlib/assert-is-number").isPrimitive,p=require("@stdlib/utils-define-read-only-property"),i=require("@stdlib/utils-define-nonenumerable-read-only-property"),h=require("@stdlib/string-format"),y=s(),f=a();function t(e,r){if(!(this instanceof t))throw new TypeError("invalid invocation. Constructor must be called with the `new` keyword.");if(!m(e))throw new TypeError(h("invalid argument. Real component must be a number. Value: `%s`.",e));if(!m(r))throw new TypeError(h("invalid argument. Imaginary component must be a number. Value: `%s`.",r));return p(this,"re",e),p(this,"im",r),this}i(t,"name","Complex128");i(t,"BYTES_PER_ELEMENT",8);i(t.prototype,"BYTES_PER_ELEMENT",8);i(t.prototype,"byteLength",16);i(t.prototype,"toString",y);i(t.prototype,"toJSON",f);v.exports=t});var w=E();module.exports=w;
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
