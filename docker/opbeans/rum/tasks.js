const { Chromeless } = require('chromeless')

var baseUrl = process.env.OPBEANS_BASE_URL || 'http://www.opbeans.com';
var url = baseUrl

function sleep(ms) {
    return new Promise(resolve => {
        setTimeout(resolve, ms)
    })
}

async function run() {
    try {
        const chromeless = new Chromeless({
            lauchChrome: true
        })

        for (; ;) {
            url = await chromeless
                .goto(url)
                .evaluate((baseUrl) => {
                    // activateLoadGeneration is defined in opbeans-frontend
                    if (typeof window.activateLoadGeneration === 'function') {
                        console.log('Activating route change load generation')
                        window.activateLoadGeneration()
                    }

                    var links = document.querySelectorAll('a[href^="/"]')
                    if (links && links.length) {
                        var i = Math.floor(Math.random() * links.length)
                        return links[i].href
                    } else {
                        return baseUrl
                    }
                }, baseUrl);
            console.log(url)
            await sleep(8000 + Math.floor(Math.random() * 10000))
        }
    } catch (e){
      run();
    }
}

run().catch(console.error.bind(console))
