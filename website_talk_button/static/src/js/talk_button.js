document.addEventListener("DOMContentLoaded", function (event) {
    const init_soft_phone = (params) => {
        let _enabledButton = true;
        for (let key in params) {
            if (!params[key]) {
                console.error(`Missing config: "${key}" for Talk Button!`);
                this._enabledPhone = false;
            }
        }
        if (!_enabledButton) {
            return;
        }
        const talkButton = document.querySelector('#talk_btn')

        let soundPlayer = document.createElement("audio");
        soundPlayer.volume = 1;
        soundPlayer.setAttribute("src", "website_talk_button/static/src/sounds/outgoing-call2.ogg");

        const {
            talkbtn_sip_user,
            talkbtn_sip_secret,
            talkbtn_exten,
            talkbtn_sip_proxy,
            talkbtn_sip_protocol,
            talkbtn_websocket
        } = params;

        var socket = null;
        try {
            socket = new JsSIP.WebSocketInterface(`${talkbtn_websocket}`);
        } catch (e) {
            console.error(e);
            return;
        }

        socket.via_transport = talkbtn_sip_protocol;
        var configuration = {
            sockets: [socket],
            ws_servers: `${talkbtn_websocket}`,
            realm: 'OdooPBX',
            display_name: `${talkbtn_sip_user}`,
            uri: `sip:${talkbtn_sip_user}@${talkbtn_sip_proxy}`,
            password: `${talkbtn_sip_secret}`,
            contact_uri: `sip:${talkbtn_sip_user}@${talkbtn_sip_proxy}`,
            register: false,
        };
        var coolPhone = new JsSIP.UA(configuration);
        // JsSIP.debug.enable('JsSIP:*');
        // JsSIP.debug.disable('JsSIP:*');
        coolPhone.start();

        coolPhone.on('connected', function (e) {
            console.log('SIP Connected')
        });

        coolPhone.on("newRTCSession", function ({session}) {
            if (session.direction === "outgoing") {
                session.connection.addEventListener("track", (e) => {
                    const remoteAudio = document.createElement('audio');
                    remoteAudio.srcObject = e.streams[0];
                    remoteAudio.play();
                });
            }
        });

        var eventHandlers = {
            'connecting': function (data) {
                talkButton.classList.add('btn-warning');
                talkButton.innerText = 'Calling ...';
                soundPlayer.play();
                soundPlayer.loop = true;

            },
            'confirmed': function (data) {
                talkButton.classList.add('btn-danger');
                talkButton.innerText = 'Hangup';
            },
            'accepted': function (data) {
                soundPlayer.pause();
                soundPlayer.currentTime = 0;
            },
            'ended': function (data) {
                talkButton.classList.remove('btn-danger', 'btn-warning');
                talkButton.innerText = "Let's Talk";
                soundPlayer.pause();
                soundPlayer.currentTime = 0;
            },
            'failed': function (data) {
                talkButton.classList.remove('btn-danger', 'btn-warning');
                talkButton.innerText = "Let's Talk";
                soundPlayer.pause();
                soundPlayer.currentTime = 0;
            }
        };

        var options = {
            'eventHandlers': eventHandlers,
            'mediaConstraints': {'audio': true, 'video': false}
        };

        var callSession = null;
        talkButton.addEventListener("click", function () {
            if (talkButton.classList.contains('btn-danger') || talkButton.classList.contains('btn-warning')) {
                callSession.terminate();
            } else {
                callSession = coolPhone.call(`sip:${talkbtn_exten}`, options);
            }
        });
    }

    fetch("/get_talk_param/", {
        headers: {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        },
        method: "POST",
        body: JSON.stringify({})
    })
        .then(res => res.json())
        .then(res => init_soft_phone(res.result));
});