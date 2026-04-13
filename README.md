# Development-Project-Security-Robot

## Setup

- Make sure that battery of vexbrain and controller are charged.
- connect battery to brain.
- Place raspberry pi and its battery onto the front of the robot so the camera is facing forward.
- Turn on raspberry pi.
- Turn on brain and connect controller and run the program.

## Vex operations

- Drive around using the joysticks (right joystick controls forwards and backwards movement, left joystick controls turning).
- Can increase or decrease the speed the robot moves at by pressing the arrows.
- Once familiar with controls you can press r1 to start recording a path.
- Drive around path you would like robot to go around and press l2 once you get to the end of your path. (Only use one joystick at a time when recording a path).
- Press R2 to run the loop.
- If you wish to pause the robot momentarily hold down the pause button and when you wish for it to continue let go of the button.
- When you want to end the loop press L2 on the robot and you will be given back control to drive around.

## Pi operations

- After creating the loop that you would like send /begin on telegram to the pi to turn on the camera.
- If the camera detects a person with a certainty of 45% a capture of what the camera sees will be taken and sent to the pi so the user can see what the pi is saying.
- On the telegram the user is able to message the word save to keep a photo of the image in the chat and if the user sends ok instead then it deletes the image.
- User is able to send /status to get a live status on the robots current conditions.
- User is able to send /capture to take a photo if they want to take a photo of something at any time.


## References
