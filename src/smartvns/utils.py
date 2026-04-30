from dataclasses import dataclass
from enum import Enum
import struct
from typing import Union, List, ClassVar, Optional
from abc import ABC

from smartvns.config import SysConfig, AccFS, GyroFS

class SampleType(Enum):
    IMU = 0
    QUAT = 1
    MAG = 2
    VNS_DATA = 3
    IMU_QUAT = 4
    DATE_TIME = 5

@dataclass
class Sample(ABC):
    timestamp: int
    # subclasses must set this classvar to their SampleType; using ClassVar so
    # dataclasses don't treat it as a field. Leave as None on the abstract base.
    type: ClassVar[Optional[SampleType]] = None

@dataclass
class IMUSample(Sample):
    type = SampleType.IMU
    gyr_x: Union[int, float]
    gyr_y: Union[int, float]
    gyr_z: Union[int, float]
    acc_x: Union[int, float]
    acc_y: Union[int, float]
    acc_z: Union[int, float]

@dataclass
class QuatSample(Sample):
    type = SampleType.QUAT
    q_x: Union[int, float]
    q_y: Union[int, float]
    q_z: Union[int, float]
    q_w: Union[int, float]

@dataclass
class MagSample(Sample):
    type = SampleType.MAG
    mag_x: Union[int, float]
    mag_y: Union[int, float]
    mag_z: Union[int, float]

@dataclass
class IMUQuatSample(Sample):
    type = SampleType.IMU_QUAT
    gyr_x: Union[int, float]
    gyr_y: Union[int, float]
    gyr_z: Union[int, float]
    acc_x: Union[int, float]
    acc_y: Union[int, float]
    acc_z: Union[int, float]
    q_x: Union[int, float]
    q_y: Union[int, float]
    q_z: Union[int, float]
    q_w: Union[int, float]

@dataclass
class VNSSample(Sample):
    type = SampleType.VNS_DATA
    voltage: Union[int, float]  # in Volts
    current: Union[int, float]  # in milliAmps
    src_voltage: Union[int, float] # in Volts
    src_current: Union[int, float] # in milliAmps
    impedance: int = 0  # derived: (src_voltage - voltage)/current * 10 - 4.8


@dataclass
class UnknownPacket:
    """A chunk of bytes the decoder could not interpret.

    Emitted when the decoder encounters a sample-type byte it doesn't
    recognize, or one whose payload size is not yet implemented (e.g.
    DATE_TIME). ``payload`` contains the unrecognized bytes from the
    type byte to the end of the buffer, hex-encoded.
    """
    type_byte: int
    payload: str

class Decoder():
    """Decode raw binary sample streams into Sample dataclass instances.

    The decoder reads a ``bytes``/``bytearray`` containing one or more
    serialized samples. Each sample starts with a single type byte
    (see `SampleType`), followed by a packed payload. The decoder
    unpacks each payload using the appropriate :mod:`struct` format and
    returns a list of corresponding `Sample` dataclass instances
    (for example, `IMUSample`, `QuatSample`, `MagSample`,
    `VNSDataSample`, or `IMUQuatSample`).

    Notes:
        - On partial or malformed data the decoder stops and returns the
          successfully decoded samples. It prints an error message when
          unpacking fails.
        - Date/time samples are currently not handled.

    Example:
        ```
        decoder = Decoder()
        samples = decoder(data)
        ```

    Raises:
        struct.error: If unpacking fails. The error is caught inside the
            decoder which prints information and returns the decoded
            samples collected so far.
    """

    par_imu = struct.Struct('<I6h')
    par_mag = struct.Struct('<I3h')
    par_quat = struct.Struct('<I4h')
    par_vns = struct.Struct('<I4h')
    par_imuquat = struct.Struct('<I6h4h')

    def __call__(self, data: bytearray) -> List[Union[Sample, UnknownPacket]]:
        d: List[Union[Sample, UnknownPacket]] = []
        try:
            while len(data) > 0:
                sample_type = data[0]

                if sample_type == SampleType.IMU.value:
                    ssize = self.par_imu.size
                    s = self.par_imu.unpack(data[1:1 + ssize])
                    d.append(IMUSample(*s))
                    data = data[1 + ssize:]
                elif sample_type == SampleType.QUAT.value:
                    ssize = self.par_quat.size
                    s = self.par_quat.unpack(data[1:1 + ssize])
                    d.append(QuatSample(*s))
                    data = data[1 + ssize:]
                elif sample_type == SampleType.MAG.value:
                    ssize = self.par_mag.size
                    s = self.par_mag.unpack(data[1:1 + ssize])
                    d.append(MagSample(*s))
                    data = data[1 + ssize:]
                elif sample_type == SampleType.VNS_DATA.value:
                    ssize = self.par_vns.size
                    s = self.par_vns.unpack(data[1:1 + ssize])
                    impedance = int((s[3] - s[1]) / s[2] * 10 - 4.8) if s[2] else 0
                    d.append(VNSSample(*s, impedance=impedance))
                    data = data[1 + ssize:]
                elif sample_type == SampleType.IMU_QUAT.value:
                    ssize = self.par_imuquat.size
                    s = self.par_imuquat.unpack(data[1:1 + ssize])
                    d.append(IMUQuatSample(*s))
                    data = data[1 + ssize:]
                else:
                    # Unrecognized type byte (includes DATE_TIME, whose
                    # payload size is not yet implemented). We can't safely
                    # re-sync without knowing the payload size, so capture
                    # the remainder for inspection and stop.
                    d.append(UnknownPacket(
                        type_byte=sample_type,
                        payload=bytes(data).hex(),
                    ))
                    break
        except struct.error as e:
            print(f"Error unpacking data: {e}")
            print(f"Remaining data length: {len(data)}")
        finally:
            return d


class Filter():
    """Filter a list of `Sample` objects by their type.

    Instantiate with a list of `SampleType` values. Calling the
    resulting object with a list of samples returns either the samples
    that match the provided types (default) or the samples that do not
    match when ``drop`` is True.

    Args:
        types (List[SampleType]): Sample types to match against.
        drop (bool): If ``False`` (default) only samples whose ``type``
            is in ``types`` are kept. If ``True``, those types are
            excluded and all other samples are kept.

    Example:
        ```
        f = Filter([SampleType.IMU, SampleType.MAG])
        filtered = f(samples)
        ```
    """

    def __init__(self, types: List[SampleType], drop: bool = False):
        self.types = types
        self.drop = drop

    def __call__(self, samples: List[Sample]) -> List[Sample]:
        if self.drop:
            return [s for s in samples if s.type not in self.types]
        else:
            return [s for s in samples if s.type in self.types]


class UnitScaler():
    """Convert raw sensor samples to human-friendly units.

    The scaler converts raw integer sensor readings into floating-point
    values using sensitivity and full-scale configuration values:

    - Accelerometer: raw -> g (uses the accelerometer full-scale index
      from :attr:`SysConfig.imu.acc_fs`).
    - Gyroscope: raw -> deg/s (uses the gyroscope full-scale index
      from :attr:`SysConfig.imu.gyro_fs`).
    - Magnetometer: raw -> milligauss (scaled by :attr:`mag_sens`).
    - Quaternion components: normalized to the range [-1, 1).
    - VNS data: voltage is scaled to Volts and current to mA.

    Args:
        config (SysConfig): System configuration used to read sensor
            full-scale settings so the scaler can choose the correct
            sensitivity factors. This config must correspond to the
            one used when the raw samples were generated.

    Example:
        ```
        scaler = UnitScaler(config)
        scaled_samples = scaler(samples)
        ```
    """

    sens = {
        'acc': {
            AccFS.FS_2G: 0.061,
            AccFS.FS_4G: 0.122,
            AccFS.FS_8G: 0.244,
            AccFS.FS_16G: 0.488
        },
        'gyr': {
            GyroFS.FS_125DPS: 4.375,
            GyroFS.FS_250DPS: 8.75,
            GyroFS.FS_500DPS: 17.50,
            GyroFS.FS_1000DPS: 35.0,
            GyroFS.FS_2000DPS: 70.0,
            GyroFS.FS_4000DPS: 140.0
        },
        'mag': 1.5 # in mgauss, from datasheet
    }

    def __init__(self, config: SysConfig):
        self.config = config

    def __call__(self, samples: List[Sample]) -> List[Sample]:

        return [self._normalize_sample(s) for s in samples]

    def _normalize_sample(self, sample: Sample) -> Sample:
        if isinstance(sample, IMUSample):
            gx = self._to_rad(sample.gyr_x)
            gy = self._to_rad(sample.gyr_y)
            gz = self._to_rad(sample.gyr_z)
            ax = self._to_mps2(sample.acc_x)
            ay = self._to_mps2(sample.acc_y)
            az = self._to_mps2(sample.acc_z)
            return IMUSample(sample.timestamp, gx, gy, gz, ax, ay, az)
        elif isinstance(sample, QuatSample):
            return QuatSample(sample.timestamp,
                              sample.q_x / 32768.0,
                              sample.q_y / 32768.0,
                              sample.q_z / 32768.0,
                              sample.q_w / 32768.0)
        elif isinstance(sample, MagSample):
            mx = sample.mag_x * self.sens['mag']
            my = sample.mag_y * self.sens['mag']
            mz = sample.mag_z * self.sens['mag']
            return MagSample(sample.timestamp, mx, my, mz)
        elif isinstance(sample, IMUQuatSample):
            gx = self._to_rad(sample.gyr_x)
            gy = self._to_rad(sample.gyr_y)
            gz = self._to_rad(sample.gyr_z)
            ax = self._to_mps2(sample.acc_x)
            ay = self._to_mps2(sample.acc_y)
            az = self._to_mps2(sample.acc_z)
            return IMUQuatSample(sample.timestamp, gx, gy, gz, ax, ay, az,
                                 sample.q_x / 32768.0,
                                 sample.q_y / 32768.0,
                                 sample.q_z / 32768.0,
                                 sample.q_w / 32768.0)
        elif isinstance(sample, VNSSample):
            voltage = sample.voltage / 100.0
            current = sample.current / 1000.0
            src_voltage = sample.src_voltage / 100.0
            src_current = sample.src_current / 1000.0
            return VNSSample(sample.timestamp, voltage, current, src_voltage, src_current,
                             impedance=sample.impedance)
        else:
            raise ValueError("Unknown sample type")

    def _to_mps2(self, raw_acc) -> float:
        return raw_acc * self.sens['acc'][self.config.imu.acc_fs] / 1000.0

    def _to_rad(self, raw_gyro) -> float:
        return raw_gyro * self.sens['gyr'][self.config.imu.gyro_fs] / 1000.0
