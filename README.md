lerobot-setup-motors \
    --robot.type=so101_follower \
    --robot.port=/dev/tty.usbmodem5AAF2196261

lerobot-setup-motors \
    --teleop.type=so101_leader \
    --teleop.port=/dev/tty.usbmodem5AAF2195131

lerobot-calibrate \
    --robot.type=so101_follower \
    --robot.port=/dev/tty.usbmodem5AAF2196261 \
    --robot.id=my_awesome_follower_arm

lerobot-calibrate \
    --teleop.type=so101_leader \
    --teleop.port=/dev/tty.usbmodem5AAF2195131 \
    --teleop.id=my_awesome_leader_arm

lerobot-teleoperate \
    --robot.type=so101_follower \
    --robot.port=/dev/tty.usbmodem5AAF2196261 \
    --robot.id=my_awesome_follower_arm \
    --teleop.type=so101_leader \
    --teleop.port=/dev/tty.usbmodem5AAF2195131 \
    --teleop.id=my_awesome_leader_arm

follower
-------------------------------------------
NAME            |    MIN |    POS |    MAX
shoulder_pan    |    745 |   2093 |   3489
shoulder_lift   |    830 |    849 |   3117
elbow_flex      |    824 |   3038 |   3055
wrist_flex      |    943 |   2402 |   3246
gripper         |   2033 |   2051 |   3565

leader
-------------------------------------------
NAME            |    MIN |    POS |    MAX
shoulder_pan    |    720 |   2020 |   3441
shoulder_lift   |    781 |    792 |   3142
elbow_flex      |    869 |   3066 |   3073
wrist_flex      |    852 |   2679 |   3180
gripper         |   2030 |   2046 |   3294