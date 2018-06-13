## remoteFoil controls Airfoil remotely

remoteFoil for airfoil provides a CLI and REST interface for Airfoil to remotely control a running Airfoil instance. The goal of the REST part of the project is not to provide a full web interface, but to provide endpoints to get information about and control an instance of Airfoil that may be running on another Mac or Windows machine. 

I'm building on the work of https://github.com/dersimn/Airfoil-Slipstream-Remote-Protocol which reverse engineered the protocol and demonstrated that work in node.js. This implementation will be written with Python 3. 

#### Sidenote  
Personally, I will be pairing this project with the 'URI switch' device in Samsung Smartthings so I can say stuff like "Alexa, connect the living room speaker" or 'Alexa, mute the bedroom speaker'. Alexa will then tell Smartthings to trigger the URI that changes the volume or connects/disconnects a speaker. If that works, then I'm creating a skill so I can control things more dynamically (Alexa, ask Airfoil which speakers are connected) this will require a node running on the local network which may be against their policy, so I may just build it and include instructions for individual implementation. 
