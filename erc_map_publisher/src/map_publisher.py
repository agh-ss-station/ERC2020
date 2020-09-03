#!/usr/bin/env python

import rospy
import numpy as np
# Because of transformations
import tf2_ros
import tf.transformations

from erc_map_publisher.srv import UpdateTransform

from geometry_msgs.msg import PoseWithCovarianceStamped, TransformStamped


def to_matrix(transform):
    t, r = transform.translation, transform.rotation
    tm = tf.transformations.translation_matrix(t)
    rm = tf.transformations.rotation_matrix(t)

    return np.dot(tm, rm)


class MapBroadcaster:
    def __init__(self):
        self.odom_frame = "odom"
        self.map_frame = "map"
        self.base_frame = "base_link"

        self.tfBuffer = tf2_ros.Buffer()
        self.listener = tf2_ros.TransformListener(self.tfBuffer)
        self.broadcaster = tf2_ros.TransformBroadcaster()

        self.transform = self._identity_transform()
        self.update_transform_srv = rospy.Service("/update_map_odom_transform", UpdateTransform, self.update_map_odom_transform)

    def update_map_odom_transform(self, req):
        self.update_transform(req.pose)
        return ["map -> odom transform updated", True]

    def publish_map(self):
        self.transform.header.stamp = rospy.Time.now()
        self.broadcaster.sendTransform(self.transform)

    def update_transform(self, map_base):
        # ugly but should work xd
        t = TransformStamped()
        t.transform.translation = map_base.pose.pose.position
        t.transform.rotation = map_base.pose.pose.orientation

        try:
            base_odom = self.tfBuffer.lookup_transform(self.base_frame,
                                                       self.odom_frame,
                                                       rospy.Time().now())

        except (tf2_ros.LookupException,
                tf2_ros.ConnectivityException,
                tf2_ros.ExtrapolationException):
            return

        self.transform = self.chain_transforms(t, base_odom)

        return 

    def _chain_transforms(self, map_base, base_odom):
        m1 = to_matrix(map_base)
        m2 = to_matrix(base_odom)
        m = np.dot(m1, m2)

        t = tf.transformations.translation_from_matrix(m)
        r = tf.transformations.rotation_from_matrix(m)

        transform = self._identity_transform()
        transform.transform.translation = t
        transform.transform.rotation = r

        return transform

    def _identity_transform(self):
        t = TransformStamped()
        t.header.frame_id = self.map_frame
        t.child_frame_id = self.odom_frame
        t.transform.rotation.w = 1

        return t


if __name__ == '__main__':
    rospy.init_node('map_broadcaster')
    broadcaster = MapBroadcaster()

    rate = rospy.Rate(10)
    while not rospy.is_shutdown():
        broadcaster.publish_map()
        rate.sleep()