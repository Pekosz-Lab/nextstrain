var should = require('should')
	, binomial = require('../src/binomial');

describe( "binomial",function(){

	it('get', function(done){

		should.equal( binomial.get(0,0), 1 );
		should.equal( binomial.get(3,3), 1 );
		should.equal( binomial.get(3,1), 3 );
		should.equal( binomial.get(3,1), 3 );
		should.equal( binomial.get(20,13), 77520 );
		should.equal( binomial.get(20,13), 77520 );
		should.equal( binomial.get(20,13), 77520 );
		should.equal( binomial.get(20,12), 125970 );
		should.equal( binomial.get(20,11), 167960 );
		should.equal( binomial.get(100, 4), 3921225 );
		should.equal( binomial.get(500, 4), 2573031125 );
		done();

	});

	it('get_no_memo', function(done){

		should.equal( binomial.get_no_memo(0,0), 1 );
		should.equal( binomial.get_no_memo(3,3), 1 );
		should.equal( binomial.get_no_memo(3,1), 3 );
		should.equal( binomial.get_no_memo(3,1), 3 );
		should.equal( binomial.get_no_memo(20,13), 77520 );
		should.equal( binomial.get_no_memo(20,13), 77520 );
		should.equal( binomial.get_no_memo(20,13), 77520 );
		should.equal( binomial.get_no_memo(20,12), 125970 );
		should.equal( binomial.get_no_memo(20,11), 167960 );
		should.equal( binomial.get_no_memo(100, 4), 3921225 );
		should.equal( binomial.get_no_memo(500, 4), 2573031125 );
		
		done();

	});

});
