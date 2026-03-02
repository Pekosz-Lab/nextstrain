var Benchmark = require('benchmark')
	, binomial = require('../src/binomial');


// callbacks for tests

function target(event) {
  console.log(String(event.target));
};

function on_complete() {
  console.log('Fastest is ' + this.filter('fastest').pluck('name'));
};

var bench_options = { 'async': false, 'minSamples': 200 };



var suite = new Benchmark.Suite;

suite.add('binomial.get 80 random', function() {

	var n = Math.ceil( Math.random() * 80 )
		, k = Math.ceil( Math.random() * 80 );

	binomial.get(n, k);

})
.add('binomial.get_no_memo 80 random', function() {

	var n = Math.ceil( Math.random() * 80 )
		, k = Math.ceil( Math.random() * 80 );

	binomial.get_no_memo(n, k);

})
.on('cycle', target )
.on('complete', on_complete)
.run(bench_options);



var high_suite = new Benchmark.Suite;

high_suite.add('binomial.get 500 random', function() {

	var n = Math.ceil( Math.random() * 500 )
		, k = Math.ceil( Math.random() * 500 );

	binomial.get(n, k);

})
.add('binomial.get_no_memo 500 random', function() {

	var n = Math.ceil( Math.random() * 500 )
		, k = Math.ceil( Math.random() * 500 );

	binomial.get_no_memo(n, k);

})
.on('cycle', target)
.on('complete', on_complete)
.run(bench_options);



var repeat_low_suite = new Benchmark.Suite;

repeat_low_suite.add('repeat binomial.get - 50 choose 10', function() {

	var n = 50
		, k = 5;

	binomial.get(n, k);

})
.add('repeat binomial.get_no_memo - 50 choose 10', function() {

	var n = 50
		, k = 5;

	binomial.get_no_memo(n, k);

})
.on('cycle', target)
.on('complete', on_complete)
.run(bench_options);




var repeat_high_suite = new Benchmark.Suite;

repeat_high_suite.add('repeat binomial.get - 500 choose 100', function() {

	var n = 500
		, k = 100;

	binomial.get(n, k);

})
.add('repeat binomial.get_no_memo - 500 choose 100', function() {

	var n = 500
		, k = 100;

	binomial.get_no_memo(n, k);

})
.on('cycle', target )
.on('complete', on_complete )
.run(bench_options);



