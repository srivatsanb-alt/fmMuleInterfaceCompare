#  Remote Drive # 

Remote drive functionality enables fleet manager dashboard users to move sherpas remotely. A peer-to-peer webrtc connection is established between the browser and the sherpa so that camera, point cloud feed from the sherpa can be streamed in the dashboard. The remote drive panel on the dashboard has a joystick which can be used to move the sherpas. The joystcik commands from the browser are sent through the same webrtc connection to the sherpas.  


# How it works # 

FM has different websocket endpoints controller(dashboard user) and the sherpas to connect. 

Controller(dashboard user) connects to websocket endpoint on the FM server and sends the sherpa name, a webrtc sdp(session description protocol))offer through the websocket connection. This is forwarded to the sherpa, sherpa in turns returns accepts webrtc connection, returns a webrtc sdp answer. With this a peer-2-peer connection can be established between the sherpa and the dashboard. FM also hosts a turn server(coturn) to relay the media streams comming from one peer to another. The turn server is used as the firewall may restrict direct peer-2-peer connection between the dashboard and the sherpa.    

Sherpa share a video stream(camera feed), data stream(filtered lidar point cloud) to the controller periodically, dashboard user share joystcik inputs via data stream to the sherpa.


## Architecture ##

![Remote drive architecture](/home/srikarthikeyan/Desktop/remote_drive_architecture.png)


## Remote drive dashboard ## 

![Remote drive Dashboard](/home/srikarthikeyan/Downloads/remote_drive_screen.png)








