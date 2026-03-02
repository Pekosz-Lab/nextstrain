"use strict";var o=function(r,i){return function(){return i||r((i={exports:{}}).exports,i),i.exports}};var a=o(function(P,u){"use strict";function m(){return String(this.value)}u.exports=m});var s=o(function(g,n){"use strict";function y(){var r={};return r.type="Float16",r.value=this.value,r}n.exports=y});var l=o(function(F,v){"use strict";function E(){return this.value}v.exports=E});var f=o(function(R,c){"use strict";var S=require("@stdlib/assert-is-number").isPrimitive,h=require("@stdlib/utils-define-read-only-property"),e=require("@stdlib/utils-define-nonenumerable-read-only-property"),q=require("@stdlib/number-float64-base-to-float16"),T=require("@stdlib/string-format"),O=require("@stdlib/assert-has-to-primitive-symbol-support"),d=require("@stdlib/symbol-to-primitive"),w=a(),b=s(),p=l();function t(r){if(!(this instanceof t))throw new TypeError("invalid invocation. Constructor must be called with the `new` keyword.");if(!S(r))throw new TypeError(T("invalid argument. Must provide a number. Value: `%s`.",r));return h(this,"value",q(r)),this}e(t,"name","Float16");e(t,"BYTES_PER_ELEMENT",2);e(t.prototype,"BYTES_PER_ELEMENT",2);e(t.prototype,"toString",w);e(t.prototype,"toJSON",b);e(t.prototype,"valueOf",p);O()&&e(t.prototype,d,p);c.exports=t});var N=f();module.exports=N;
/**
* @license Apache-2.0
*
* Copyright (c) 2025 The Stdlib Authors.
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
