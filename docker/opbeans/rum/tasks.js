const puppeteer = require('puppeteer')

const baseUrl = process.env.OPBEANS_BASE_URL || 'http://www.opbeans.com';
let url = baseUrl

function sleep(ms) {
    return new Promise(resolve => {
        setTimeout(resolve, ms)
    })
}

async function run() {
  const browser = await puppeteer.launch({
    pipe: true,
    headless: true,
    dumpio: true,
    //waitForInitialPage: false,
    //devtools: false,
    //ignoreDefaultArgs: false,
    args: [
      '--disable-dev-shm-usage',
      // debug port is exported
      //'--remote-debugging-address=0.0.0.0',
      //'--remote-debugging-port=9222',
      // chromium need to use --no-sandbox on linux/arm64
      // '--disable-gpu-sandbox',
      // '--disable-namespace-sandbox',
      '--disable-setuid-sandbox',
      '--no-sandbox',
      '--no-zygote',
      '--disable-gpu',
      '--disable-audio-output',
      // '--disable-gpu-rasterization',
      //'--no-first-run',
      //'--safe-mode',
      // the pipe is broken sometimes with a single process does not happen
      '--headless',
      '--single-process'
    ] // see https://github.com/puppeteer/puppeteer/blob/master/docs/troubleshooting.md#tips
    // https://peter.sh/experiments/chromium-command-line-switches/
  })
  debugger;
  const page = await browser.newPage()
  page.on('console', msg => console.log(
    'PAGE LOG:', msg.type() + "\t" + msg.text() + "\t" + msg.location().url + " (" + msg.location().lineNumber + ":" + msg.location().columnNumber + ")")
  )
  for (; ;) {
    try {
      await page.goto(url)
      console.log('Checking URL:' + url);
      url = await page.evaluate(defaultUrl => {
          // activateLoadGeneration is defined in opbeans-frontend
          if (typeof window.activateLoadGeneration === 'function') {
            console.log('Activating route change load generation')
            window.activateLoadGeneration()
          }
          const links = document.querySelectorAll('a[href^="/"]')
          if (links && links.length) {
              const i = Math.floor(Math.random() * links.length)
              return links[i].href
          } else {
              return defaultUrl
          }
        },
        baseUrl
      )
    } catch (e) {
      // this will catch the error, log it and let the process continue
      console.error(`Error occurred while evaluating ${url}:`, e)
    }
    console.log(url)
    await sleep(8000 + Math.floor(Math.random() * 10000))
  }
}

run().catch(console.error.bind(console))
