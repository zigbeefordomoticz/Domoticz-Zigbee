import unittest

from Zigbee.helperDefautResponse import (
    must_send_default_response,
    response_required_commands,
)


class TestMustSendDefaultResponse(unittest.TestCase):

    # ------------------------------------------------------------
    # Disable Default Response flag behavior
    # ------------------------------------------------------------
    def test_disable_default_response_bit(self):
        frame_control = 0x10  # bit 4 = disable default response
        self.assertFalse(
            must_send_default_response(
                frame_control=frame_control,
                command_id=0x00,
                cluster_id=0x0000
            )
        )

    def test_enable_default_response_bit(self):
        frame_control = 0x00
        self.assertTrue(
            must_send_default_response(
                frame_control=frame_control,
                command_id=0xFF,   # random command not in response_required list
                cluster_id=0x1234
            )
        )

    # ------------------------------------------------------------
    # OTA Cluster (0x0019) special behavior
    # ------------------------------------------------------------
    def test_ota_success_no_default_response(self):
        # OTA cluster should NOT send DR on success
        self.assertFalse(
            must_send_default_response(
                frame_control=0x00,
                command_id=0x00,
                cluster_id=0x0019,
                status=0x00
            )
        )

    def test_ota_error_default_response(self):
        # OTA must send DR on error
        self.assertTrue(
            must_send_default_response(
                frame_control=0x00,
                command_id=0x00,
                cluster_id=0x0019,
                status=0x01
            )
        )

    # ------------------------------------------------------------
    # Commands that expect a specific response
    # ------------------------------------------------------------
    def test_response_required_success_no_dr(self):
        # 0x0000 cluster Read Attributes requires specific response
        self.assertFalse(
            must_send_default_response(
                frame_control=0x00,
                command_id=0x00,
                cluster_id=0x0000,
                status=0x00
            )
        )

    def test_response_required_error_dr(self):
        # error → must send default response
        self.assertTrue(
            must_send_default_response(
                frame_control=0x00,
                command_id=0x00,
                cluster_id=0x0000,
                status=0xFF
            )
        )

    # ------------------------------------------------------------
    # Clusters with defined response-required commands
    # ------------------------------------------------------------
    def test_cluster_0702_specific_command(self):
        # Smart Energy Metering (0x0702) has many response-required commands
        cmd = list(response_required_commands[0x0702])[0]
        self.assertFalse(
            must_send_default_response(
                frame_control=0x00,
                command_id=cmd,
                cluster_id=0x0702,
                status=0x00
            )
        )

    def test_cluster_0201_error(self):
        # Thermostat → error must generate DR
        cmd = list(response_required_commands[0x0201])[0]
        self.assertTrue(
            must_send_default_response(
                frame_control=0x00,
                command_id=cmd,
                cluster_id=0x0201,
                status=0x01
            )
        )

    # ------------------------------------------------------------
    # Report Attributes (0x0A) has no dedicated response: unlike
    # Read/Discover Attributes, it must fall back to a Default
    # Response when the sender requests one (bit not set), otherwise
    # the sender never gets acked and retransmits indefinitely.
    # ------------------------------------------------------------
    def test_report_attributes_requires_default_response(self):
        self.assertTrue(
            must_send_default_response(
                frame_control=0x08,  # Disable Default Response bit NOT set
                command_id=0x0A,     # Report Attributes
                cluster_id=0x0000,
                status=0x00
            )
        )

    # ------------------------------------------------------------
    # Commands NOT in response-required table
    # ------------------------------------------------------------
    def test_unknown_cluster_default_response(self):
        # Unknown cluster → always send DR
        self.assertTrue(
            must_send_default_response(
                frame_control=0x00,
                command_id=0x01,
                cluster_id=0x9999,   # non-existent cluster
                status=0x00
            )
        )

    def test_known_cluster_but_unknown_command(self):
        # Known cluster but command not in response_required → DR must be sent
        self.assertTrue(
            must_send_default_response(
                frame_control=0x00,
                command_id=0x99,
                cluster_id=0x0000,
                status=0x00
            )
        )

    # ------------------------------------------------------------
    # Status behavior
    # ------------------------------------------------------------
    def test_error_always_generates_dr_if_no_other_response(self):
        # Unknown cluster + error → DR
        self.assertTrue(
            must_send_default_response(
                frame_control=0x00,
                command_id=0x04,
                cluster_id=0x5555,
                status=0x01
            )
        )


if __name__ == '__main__':
    unittest.main()
