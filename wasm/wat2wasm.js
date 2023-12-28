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
        // binaryBuffer is Uint8Array
        const outputBase64 = btoa(String.fromCharCode.apply(null, binaryBuffer));

        // send debug details to stderr
        console.error({ binaryOutput, outputLog, binaryBuffer })
        // send base64 wasm binary to stdout
        console.log(outputBase64)

        // test that fib works!
        const wasmBuffer = Buffer.from(outputBase64, 'base64');
        WebAssembly.instantiate(wasmBuffer, {})
            .then(result => {
                const func = result.instance.exports.fib;
                console.log('Calling with:', 10)
                console.log('Result:', func(10));
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
