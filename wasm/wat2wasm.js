const wabtmodule = require('./wabtmodule')

const compile = (source) => {
    wabtmodule().then(function (wabt) {
        const features = {}
        const module = wabt.parseWat('test.wast', source, features);
        module.resolveNames();
        module.validate(features);
        const binaryOutput = module.toBinary({ log: true, write_debug_names: true });
        const outputLog = binaryOutput.log;
        const binaryBuffer = binaryOutput.buffer;

        // send debug details to stderr
        console.error({ binaryOutput, outputLog, binaryBuffer })

        // test that fib works!
        WebAssembly.instantiate(binaryBuffer, {})
            .then(result => {
                const func = result.instance.exports.fib;
                console.log('Calling with:', 25)
                const t = performance.now();
                console.log('Result:', func(25));
                console.log('Time:', performance.now() - t);
            })
            .catch(error => {
                console.error('Error loading WebAssembly module:', error);
            });
    })
}

let source = '';
process.stdin.setEncoding('utf-8');
process.stdin.on('data', (chunk) => {
    source += chunk;
});
process.stdin.on('end', () => {
    compile(source)
});
process.stdin.on('error', (err) => {
    console.error(err);
});
