module.exports = {
    apps : [{
        name: "chrome",
        script: "google-chrome",
        args: "--remote-debugging-address=0.0.0.0 --remote-debugging-port=9222 --disable-gpu --headless",
        exec_interpreter: "none",
        exec_mode: "fork",
        restart_delay: 2000
    }, {
        name: "worker",
        script: "./tasks.js",
        instances: 1,
    }]
}
