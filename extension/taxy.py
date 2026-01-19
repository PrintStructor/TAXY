from math import sqrt
from . import taxy_utl as utl
from .taxy_utl import NozzleNotFoundException
import logging
import json


class taxy:
    __FRAME_WIDTH = 1280
    __FRAME_HEIGHT = 720

    def __init__(self, config):
        # Load config values
        self.camera_url = config.get("nozzle_cam_url")
        self.server_url = config.get("server_url")
        self.speed = config.getfloat("move_speed", 1800.0, above=10.0)
        self.calib_iterations = config.getint(
            "calib_iterations", 1, minval=1, maxval=25
        )
        self.calib_value = config.getfloat("calib_value", 1.0, above=0.25)
        self.save_training_images = config.getboolean("save_training_images", False)
        self.detection_tolerance = config.getint(
            "detection_tolerance", 0, minval=0, maxval=5
        )

        # Initialize variables
        self.mpp = None  # Average mm per pixel
        self.is_calibrated = False  # Is the camera calibrated
        self.last_nozzle_center_successful = False  # Was the last calibration successful

        # List of space coordinates for each calibration point
        self.space_coordinates = []

        # List of camera coordinates for each calibration point
        self.camera_coordinates = []
        self.mm_per_pixels = []  # List of mm per pixel for each calibration point
        self.cp = None  # Center position used for offset calculations
        self.last_calculated_offset = [0, 0]

        # Load used objects.
        self.config = config
        self.printer = config.get_printer()
        self.gcode = self.printer.lookup_object("gcode")

        # Register event handlers.
        self.printer.register_event_handler("klippy:ready", self.handle_ready)

    def handle_ready(self):
        self.reactor = self.printer.get_reactor()
        self.pm = utl.taxy_pm(self.config)  # Printer Manager

        # IMPORTANT:
        # Klipper treats commands with letters+digits as a single token (e.g. "KTAY8"),
        # so "KTAY8_START_PREVIEW" becomes malformed.
        # Therefore we register KTAY_* commands instead of KTAY8_*.
        self.gcode.register_command(
            "KTAY_CALIB_CAMERA",
            self.cmd_KTAY8_CALIB_CAMERA,
            desc=self.cmd_KTAY8_CALIB_CAMERA_help,
        )
        self.gcode.register_command(
            "KTAY_FIND_NOZZLE_CENTER",
            self.cmd_FIND_NOZZLE_CENTER,
            desc=self.cmd_FIND_NOZZLE_CENTER_help,
        )
        self.gcode.register_command(
            "KTAY_SET_ORIGIN", self.cmd_SET_CENTER, desc=self.cmd_SET_CENTER_help
        )
        self.gcode.register_command(
            "KTAY_GET_OFFSET", self.cmd_GET_OFFSET, desc=self.cmd_GET_OFFSET_help
        )
        self.gcode.register_command(
            "KTAY_MOVE_TO_ORIGIN",
            self.cmd_MOVE_TO_ORIGIN,
            desc=self.cmd_MOVE_TO_ORIGIN_help
        )
        self.gcode.register_command(
            "KTAY_SIMPLE_NOZZLE_POSITION",
            self.cmd_SIMPLE_NOZZLE_POSITION,
            desc=self.cmd_SIMPLE_NOZZLE_POSITION_help,
        )
        self.gcode.register_command(
            "KTAY_SEND_SERVER_CFG",
            self.cmd_SEND_SERVER_CFG,
            desc=self.cmd_SEND_SERVER_CFG_help,
        )
        self.gcode.register_command(
            "KTAY_START_PREVIEW",
            self.cmd_START_PREVIEW,
            desc=self.cmd_START_PREVIEW_help,
        )
        self.gcode.register_command(
            "KTAY_STOP_PREVIEW",
            self.cmd_STOP_PREVIEW,
            desc=self.cmd_STOP_PREVIEW_help,
        )

    cmd_START_PREVIEW_help = "Send the server command to start the preview"

    def cmd_START_PREVIEW(self, gcmd):
        self._preview(gcmd, action="start")

    cmd_STOP_PREVIEW_help = "Send the server command to stop the preview"

    def cmd_STOP_PREVIEW(self, gcmd):
        self._preview(gcmd, action="stop")

    def _preview(self, gcmd, action="start"):
        try:
            rr = utl.send_srv_command(self.server_url, "/preview", action=action)
            gcmd.respond_info("kTAY8 Server response: %s" % str(rr))
        except Exception as e:
            raise self.gcode.error(
                "Failed to send preview command to server, got error: %s" % str(e)
            )

    cmd_SEND_SERVER_CFG_help = (
        "Send the server configuration to the server, i.e. the nozzle camera url"
    )

    def cmd_SEND_SERVER_CFG(self, gcmd):
        try:
            _camera_url = gcmd.get("CAMERA_URL", self.camera_url)
            rr = utl.send_srv_command(
                self.server_url,
                "/set_server_cfg",
                camera_url=_camera_url,
                save_training_images=self.save_training_images,
                detection_tolerance=self.detection_tolerance,
            )
            gcmd.respond_info("kTAY8 Server response: %s" % str(rr))
        except Exception as e:
            raise self.gcode.error(
                "Failed to send server configuration to server, got error: %s" % str(e)
            )

    cmd_SET_CENTER_help = (
        "Saves the center position for offset calculations"
        + "based on the current toolhead position."
    )

    def cmd_SET_CENTER(self, gcmd):
        self.cp = self.pm.get_raw_position()
        self.cp = (round(float(self.cp[0]), 3), round(float(self.cp[1]), 3))
        self.gcode.respond_info(
            "Center position set to X:%3f Y:%3f" % (self.cp[0], self.cp[1])
        )

    cmd_GET_OFFSET_help = (
        "Get offset from the current position to the configured center position"
    )

    def cmd_GET_OFFSET(self, gcmd):
        if self.cp is None:
            raise self.gcode.error(
                "No center position set, use KTAY_SET_ORIGIN to set it to the"
                + " position you want to get offset from"
            )
            return
        _pos = self.pm.get_raw_position()
        self.last_calculated_offset = (
            round((float(_pos[0]) - self.cp[0]), 3),
            round((float(_pos[1]) - self.cp[1]), 3),
        )

        self.gcode.respond_info(
            "Offset from center is X:%.3f Y:%.3f"
            % (self.last_calculated_offset[0], self.last_calculated_offset[1])
        )

    cmd_MOVE_TO_ORIGIN_help = (
        "Move to saved origin using RAW coordinates (ignoring tool offsets). "
        "Use after tool change to return to calibration position."
    )

    def cmd_MOVE_TO_ORIGIN(self, gcmd):
        if self.cp is None:
            raise self.gcode.error(
                "No origin set. Use KTAY_SET_ORIGIN first to save the reference position."
            )
        self.pm.ensureHomed()

        # Move to saved origin using RAW coordinates
        self.pm.moveAbsoluteRaw(X=self.cp[0], Y=self.cp[1], moveSpeed=self.speed)

        self.gcode.respond_info(
            "Moved to origin (RAW) X:%.3f Y:%.3f" % (self.cp[0], self.cp[1])
        )

    cmd_FIND_NOZZLE_CENTER_help = (
        "Finds the center of the nozzle and moves"
        + " it to the center of the camera, offset can be set from here"
    )

    def cmd_FIND_NOZZLE_CENTER(self, gcmd):
        ##############################
        # Calibration of the tool
        ##############################
        self.last_nozzle_center_successful = False
        self._calibrate_nozzle(gcmd)

    cmd_SIMPLE_NOZZLE_POSITION_help = (
        "Detects if a nozzle is found in the current image"
    )

    def cmd_SIMPLE_NOZZLE_POSITION(self, gcmd):
        ##############################
        # Get nozzle position
        ##############################
        logging.debug("*** calling SIMPLE_NOZZLE_POSITION")
        try:
            _response = utl.get_nozzle_position(self.server_url, self.reactor)
            if _response is None:
                raise self.gcode.error("Did not find nozzle, aborting")
            else:
                self.gcode.respond_info(
                    "Found nozzle at position: %s after %.2f seconds"
                    % (str(_response["data"]), float(_response["runtime"]))
                )
        except Exception as e:
            raise self.gcode.error(
                "Failed to run nozzle detection, got error: %s" % str(e)
            )

    cmd_KTAY8_CALIB_CAMERA_help = (
        "Calibrates the movement of the active nozzle"
        + " around the point it started at"
    )

    def cmd_KTAY8_CALIB_CAMERA(self, gcmd):
        self.gcode.respond_info("Starting mm/px calibration")
        self._calibrate_px_mm(gcmd)

    def _calibrate_px_mm(self, gcmd):
        ##############################
        # Calibration of the camera
        ##############################
        logging.debug("*** calling ktay8.getDistance")
        self.space_coordinates = []
        self.camera_coordinates = []
        self.mm_per_pixels = []

        # Setup camera calibration move coordinates
        calibration_coordinates = [
            [0, -0.5],
            [0.294, -0.405],
            [0.476, -0.155],
            [0.476, 0.155],
            [0.294, 0.405],
            [0, 0.5],
            [-0.294, 0.405],
            [-0.476, 0.155],
            [-0.476, -0.155],
            [-0.294, -0.405],
        ]

        guessPosition = [1, 1]

        try:
            self.pm.ensureHomed()
            _rr = utl.get_nozzle_position(self.server_url, self.reactor)

            # If we did not get a response at first query, abort
            if _rr is None:
                self.gcode.respond_info("Did not find nozzle, aborting")
                return

            # Save the 2D coordinates of where the nozzle is on the camera
            _uv = json.loads(_rr["data"])

            # Save the position of the nozzle in the as old (move from) value
            _olduv = _uv

            # Save the 3D coordinates of where the nozzle is on the printer
            _xy = self.pm.get_gcode_position()

            for i in range(len(calibration_coordinates)):
                _rr = _xy = None
                # Move to calibration location and get the nozzle position
                # If it is not found, skip this calibration point
                try:
                    _rr, _xy = self.move_relative_and_get_nozzle_position(
                        calibration_coordinates[i][0],
                        calibration_coordinates[i][1],
                        gcmd,
                    )
                except NozzleNotFoundException:
                    _rr = None  # Skip this calibration point

                # If we did not get a response, skip this calibration point
                if _rr is None:
                    self.pm.moveRelative(
                        X=-calibration_coordinates[i][0],
                        Y=-calibration_coordinates[i][1],
                    )
                    self.gcode.respond_info(
                        "MM per pixel for step %s of %s failed."
                        % (str(i + 1), str(len(calibration_coordinates)))
                    )
                    continue

                # If we did get a response, do the calibration point
                _uv = json.loads(_rr["data"])

                # Calculate mm per pixel and save it to a list
                mpp = self.getMMperPixel(calibration_coordinates[i], _olduv, _uv)

                # Save the 3D space coordinates, 2D camera coordinates and mm/px
                self._save_coordinates_for_matrix(_xy, _uv, mpp)
                self.gcode.respond_info(
                    "MM per pixel for step %s of %s is %s"
                    % (str(i + 1), str(len(calibration_coordinates)), str(mpp))
                )

                # If this is not the last item
                if i < (len(calibration_coordinates) - 1):
                    self.pm.moveRelative(
                        X=-calibration_coordinates[i][0],
                        Y=-calibration_coordinates[i][1],
                    )

            # Finish the calibration loop
            gcmd.respond_info("Moving back to starting position")

            if _rr is not None:
                try:
                    _rr, _xy = self.move_relative_and_get_nozzle_position(
                        -calibration_coordinates[i][0],
                        -calibration_coordinates[i][1],
                        gcmd,
                    )
                except NozzleNotFoundException:
                    _rr = None

                if _rr is None:
                    _uv = _olduv = None
                else:
                    _olduv = _uv
                    _uv = json.loads(_rr["data"])

                    mpp = self.getMMperPixel(calibration_coordinates[i], _olduv, _uv)
                    self._save_coordinates_for_matrix(_xy, _uv, mpp)
                    self.gcode.respond_info(
                        "Calibrated camera center: mm/pixel found: %.4f" % (mpp)
                    )

            # Check that we have at least 75% of the calibration points
            if len(self.mm_per_pixels) < (len(calibration_coordinates) * 0.75):
                raise self.gcode.error(
                    "More than 25% of the calibration points failed, aborting"
                )

            # Calculate the average mm per pixel
            gcmd.respond_info("Calculating average mm per pixel")
            self.mpp = self._get_average_mpp_from_lists(gcmd)

            # Calculate transformation matrix
            self.transform_input = [
                (
                    self.space_coordinates[i],
                    utl.normalize_coords(camera),
                )
                for i, camera in enumerate(self.camera_coordinates)
            ]

            # Calculate the transformation matrix on the server where we have NumPy installed
            if not (
                utl.calculate_camera_to_space_matrix(
                    self.server_url, self.transform_input
                )
            ):
                raise self.gcode.error("Failed to calculate camera to space matrix")

            # Calculate the required values for calculating pixel to mm position
            _current_position = self.pm.get_gcode_position()
            _cx, _cy = utl.normalize_coords(_uv)
            _v = [_cx**2, _cy**2, _cx * _cy, _cx, _cy, 0]

            _offsets = json.loads(utl.calculate_offset_from_matrix(self.server_url, _v))

            guessPosition[0] = round(_offsets[0], 3) + round(_current_position[0], 3)
            guessPosition[1] = round(_offsets[1], 3) + round(_current_position[1], 3)

            self.pm.moveAbsolute(X=guessPosition[0], Y=guessPosition[1])
            try:
                _rr = utl.get_nozzle_position(self.server_url, self.reactor)
            except NozzleNotFoundException:
                pass

            self.is_calibrated = True
            logging.debug("*** exiting ktay8.getDistance")

        except Exception as e:
            raise self.gcode.error("_calibrate_px_mm failed %s" % str(e)).with_traceback(
                e.__traceback__
            )

    def _calibrate_nozzle(self, gcmd, retries=30):
        ##############################
        # Calibration of the tool
        ##############################
        logging.debug("*** calling ktay8._calibrate_Tool")
        _retries = 0
        _not_found_retries = 0
        _uv = [None, None]
        _xy = [None, None]
        _cx = 0
        _cy = 0
        _olduv = None
        _pixel_offsets = [None, None]
        _offsets = [None, None]
        _rr = None

        try:
            self.pm.ensureHomed()

            if not self.is_calibrated:
                raise self.gcode.error("Camera is not calibrated, aborting")

            for _retries in range(retries):
                _rr = utl.get_nozzle_position(self.server_url, self.reactor)

                if _rr is None:
                    if _not_found_retries > 3:
                        raise self.gcode.error("Did not find nozzle, aborting")
                    self.gcode.respond_info(
                        "Did not find nozzle, Will try to"
                        + " wiggle the toolhead to find it"
                    )
                    if _not_found_retries == 0:
                        self.pm.moveRelative(X=0.1)
                    elif _not_found_retries == 1:
                        self.pm.moveRelative(X=-0.2)
                    elif _not_found_retries == 2:
                        self.pm.moveRelative(X=0.1, Y=0.1)
                    elif _not_found_retries == 3:
                        self.pm.moveRelative(Y=-0.2)
                    _not_found_retries += 1
                    continue
                else:
                    _not_found_retries = 0

                _uv = json.loads(_rr["data"])

                if _olduv is None:
                    _olduv = _uv

                _xy = self.pm.get_gcode_position()

                _cx, _cy = utl.normalize_coords(_uv)
                _v = [_cx**2, _cy**2, _cx * _cy, _cx, _cy, 0]

                _offsets = json.loads(
                    utl.calculate_offset_from_matrix(self.server_url, _v)
                )

                _offsets[0] = round(_offsets[0], 3)
                _offsets[1] = round(_offsets[1], 3)

                self.gcode.respond_info(
                    "*** Nozzle calibration take: "
                    + str(_retries)
                    + ".\n X"
                    + str(round(_xy[0], 2))
                    + " Y"
                    + str(round(_xy[1], 2))
                    + " \nUV: "
                    + str(_uv)
                    + " old UV: "
                    + str(_olduv)
                    + " \nOffset X: "
                    + str(round(_offsets[0], 2))
                    + " \nOffset Y: "
                    + str(round(_offsets[1], 2))
                )

                if _offsets[0] != 0.0 or _offsets[1] != 0.0:
                    _pixel_offsets[0] = _offsets[0] / self.mpp
                    _pixel_offsets[1] = _offsets[1] / self.mpp

                    if (
                        _pixel_offsets[0] + _uv[0] > self.__FRAME_WIDTH
                        or _pixel_offsets[1] + _uv[1] > self.__FRAME_HEIGHT
                        or _pixel_offsets[0] + _uv[0] < 0
                        or _pixel_offsets[1] + _uv[1] < 0
                    ):
                        raise self.gcode.error(
                            "Calibration failed, offset would move"
                            + " the nozzle outside the frame. This is"
                            + " most likely caused by a bad mm/px"
                            + " calibration"
                        )

                    _olduv = _uv
                    self.pm.moveRelative(X=_offsets[0], Y=_offsets[1], moveSpeed=1000)
                    continue
                elif _offsets[0] == 0.0 and _offsets[1] == 0.0:
                    self.gcode.respond_info("Calibration to nozzle center complete")
                    self.last_nozzle_center_successful = True
                    return

        except Exception as e:
            logging.exception(
                "_calibrate_nozzle(): self.mpp: "
                + str(self.mpp)
                + " _pixel_offsets: "
                + str(_pixel_offsets)
                + " _uv: "
                + str(_uv)
                + " _offsets: "
                + str(_offsets)
                + " _olduv: "
                + str(_olduv)
                + " _xy: "
                + str(_xy)
                + " _retries: "
                + str(_retries)
                + " _not_found_retries: "
                + str(_not_found_retries)
                + " _rr: "
                + str(_rr)
            )

            raise self.gcode.error(e).with_traceback(e.__traceback__)

    def getMMperPixel(self, distance_traveled=[], from_camera_point=[], to_camera_point=[]):
        logging.debug("*** calling ktay8.getMMperPixel")
        logging.debug("distance_traveled: %s" % str(distance_traveled))
        logging.debug("from_camera_point: %s" % str(from_camera_point))
        logging.debug("to_camera_point: %s" % str(to_camera_point))
        total_distance_traveled = abs(distance_traveled[0]) + abs(distance_traveled[1])
        logging.debug("total_distance_traveled: %s" % str(total_distance_traveled))
        mpp = round(
            total_distance_traveled
            / self.getDistance(
                from_camera_point[0],
                from_camera_point[1],
                to_camera_point[0],
                to_camera_point[1],
            ),
            3,
        )
        logging.debug("mm per pixel: %s" % str(mpp))
        logging.debug("*** exiting ktay8.getMMperPixel")
        return mpp

    def move_relative_and_get_nozzle_position(self, X, Y, gcmd):
        self.pm.moveRelative(X=X, Y=Y)

        _request_result = utl.get_nozzle_position(self.server_url, self.reactor)

        if _request_result is None:
            return None, None

        _current_position = self.pm.get_gcode_position()

        return _request_result, [_current_position[0], _current_position[1]]

    def _save_coordinates_for_matrix(self, space_coordinates, camera_coordinates, mpp):
        self.space_coordinates.append(space_coordinates)
        self.camera_coordinates.append(camera_coordinates)
        self.mm_per_pixels.append(mpp)

    def _get_average_mpp_from_lists(self, gcmd):
        logging.debug("*** calling ktay8._get_average_mpp_from_lists")
        try:
            (
                mpp,
                new_mm_per_pixels,
                new_space_coordinates,
                new_camera_coordinates,
            ) = utl.get_average_mpp(
                self.mm_per_pixels,
                self.space_coordinates,
                self.camera_coordinates,
                gcmd,
            )

            if mpp is None:
                raise self.gcode.error("Failed to get average mm per pixel")
            elif len(new_mm_per_pixels) < (len(self.mm_per_pixels) * 0.75):
                raise self.gcode.error(
                    "More than 25% of the calibration points failed, aborting"
                )

            self.mm_per_pixels = new_mm_per_pixels
            self.space_coordinates = new_space_coordinates
            self.camera_coordinates = new_camera_coordinates

            logging.debug("*** exiting ktay8._get_average_mpp_from_lists")
            return mpp
        except Exception as e:
            raise self.gcode.error(
                "_get_average_mpp_from_lists failed %s" % str(e)
            ).with_traceback(e.__traceback__)

    def getDistance(self, x1, y1, x0, y0):
        logging.debug("*** calling ktay8.getDistance")
        x1_float = float(x1)
        x0_float = float(x0)
        y1_float = float(y1)
        y0_float = float(y0)
        x_dist = (x1_float - x0_float) ** 2
        y_dist = (y1_float - y0_float) ** 2
        retVal = sqrt((x_dist + y_dist))
        returnVal = round(retVal, 3)
        logging.debug("*** exiting ktay8.getDistance")
        return returnVal

    def get_status(self, eventtime=None):
        status = {
            "last_calculated_offset": self.last_calculated_offset,
            "mm_per_pixels": self.mpp,
            "is_calibrated": self.is_calibrated,
            "save_training_images": self.save_training_images,
            "camera_center_coordinates": self.cp,
            "travel_speed": self.speed,
            "last_nozzle_center_successful": self.last_nozzle_center_successful,
        }
        return status


def load_config(config):
    return taxy(config)