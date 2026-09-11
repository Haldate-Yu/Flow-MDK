#!/usr/bin/env python
"""Minimal SELAFIN (Serafin) reader for TELEMAC-MASCARET outputs.

Handles the layouts observed in the v8p4 example/output files:

- header: title, (nbvar, nbvar_units), 32-char variable names, 10 params,
  optional 6-int date record(s), mesh (nelem/npoin/ndp), IKLE, IPOBO, X, Y;
- body: either the classic layout (NTIMES + float64 time array + frames) or
  the interleaved layout of recent writers (per time step: one float32 time
  record followed by one record per variable). The body is scanned once and
  frame byte offsets are cached, so :meth:`frame` reads a single record.

Usage
-----
    from selafin import Selafin
    slf = Selafin("r2d_gouttedo.slf")
    print(slf.variables, slf.times)
    h = slf.frame("WATER DEPTH", 5)          # [NPOIN] at time index 5
    all_h = slf.all_frames("WATER DEPTH")    # [NTIMES, NPOIN]
"""

from __future__ import annotations

import struct
from pathlib import Path

import numpy as np

__all__ = ["Selafin", "read_selafin"]


class Selafin:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        with open(self.path, "rb") as fh:
            self._parse_header(fh)
            self._scan_body(fh)

    # ------------------------------------------------------------------ #
    # header
    # ------------------------------------------------------------------ #
    @staticmethod
    def _read_record(fh) -> bytes:
        head = fh.read(4)
        if len(head) < 4:
            raise EOFError("Unexpected end of SELAFIN file")
        (length,) = struct.unpack(">i", head)
        payload = fh.read(length)
        (check,) = struct.unpack(">i", fh.read(4))
        if check != length:
            raise ValueError("Corrupted SELAFIN record framing")
        return payload

    def _parse_header(self, fh) -> None:
        self.title = self._read_record(fh).decode("utf-8", "replace").strip()
        count_payload = self._read_record(fh)
        counts = struct.unpack(f">{len(count_payload) // 4}i", count_payload)
        self.nbvars = counts[0]
        self.variables = [
            self._read_record(fh).decode("utf-8", "replace").strip()
            for _ in range(self.nbvars)
        ]
        self.params = struct.unpack(">10i", self._read_record(fh))
        # some writers append 6-int date/time records; consume defensively
        while True:
            pos = fh.tell()
            head = fh.read(4)
            if len(head) < 4:
                raise EOFError("Truncated header")
            (rec_len,) = struct.unpack(">i", head)
            if rec_len == 24:
                fh.seek(pos)
                self._read_record(fh)
            else:
                fh.seek(pos)
                break
        mesh = struct.unpack(">4i", self._read_record(fh))
        self.nelem, self.npoin, self.ndp, self.nplan = mesh
        self.ndim = self.ndp
        self.ikle = np.frombuffer(self._read_record(fh), dtype=">i4").astype(
            np.int64
        ).reshape(self.nelem, self.ndp)
        self.ipobo = np.frombuffer(self._read_record(fh), dtype=">i4").astype(np.int64)
        self.x = np.frombuffer(self._read_record(fh), dtype=">f4").astype(np.float64)
        self.y = np.frombuffer(self._read_record(fh), dtype=">f4").astype(np.float64)

    # ------------------------------------------------------------------ #
    # body scanning
    # ------------------------------------------------------------------ #
    def _scan_body(self, fh) -> None:
        frame_bytes = 4 + self.npoin * 4 + 4
        times: list[float] = []
        offsets: list[list[int]] = []  # per time step, per variable

        # try the classic layout first: NTIMES + float64 time array
        pos = fh.tell()
        head = fh.read(4)
        ntimes_candidate = None
        if len(head) == 4:
            (ntimes_candidate,) = struct.unpack(">i", head)
        classic = False
        if ntimes_candidate and ntimes_candidate > 0:
            (time_len,) = struct.unpack(">i", fh.read(4))
            if time_len == 8 * ntimes_candidate:
                classic = True
                fh.seek(pos)
                (self.ntimes,) = struct.unpack(">i", self._read_record(fh))
                self.times = np.frombuffer(
                    self._read_record(fh), dtype=">f8"
                ).astype(np.float64)
                base = fh.tell()
                for _ in range(self.ntimes):
                    offsets.append(
                        [base + (t * self.nbvars + v) * frame_bytes
                         for v in range(self.nbvars)]
                    )
                    base += self.nbvars * frame_bytes

        if not classic:
            fh.seek(pos)
            while True:
                pos = fh.tell()
                head = fh.read(4)
                if len(head) < 4:
                    break
                (rec_len,) = struct.unpack(">i", head)
                if rec_len == 4:  # interleaved float32 time marker
                    (tval,) = struct.unpack(">f", fh.read(4))
                    fh.read(4)  # trailing length
                    times.append(float(tval))
                    offsets.append([])
                elif rec_len == self.npoin * 4:
                    if not offsets:
                        raise ValueError("Frame before any time record")
                    offsets[-1].append(pos)  # record start (length prefix included)
                    fh.seek(pos + frame_bytes)
                else:
                    raise ValueError(
                        f"Unrecognised record length {rec_len} at offset {pos}"
                    )
            self.times = np.asarray(times, dtype=np.float64)
            self.ntimes = len(times)

        self._frame_offsets = offsets

    # ------------------------------------------------------------------ #
    # accessors
    # ------------------------------------------------------------------ #
    def _var_index(self, name: str) -> int:
        upper = [v.upper() for v in self.variables]
        key = name.upper()
        if key not in upper:
            raise KeyError(
                f"Variable '{name}' not in {self.path.name}; available: {self.variables}"
            )
        return upper.index(key)

    def frame(self, variable: str, time_index: int) -> np.ndarray:
        """One frame of one variable: [NPOIN] float array."""
        ivar = self._var_index(variable)
        offset = self._frame_offsets[time_index][ivar]
        with open(self.path, "rb") as fh:
            fh.seek(offset)
            (length,) = struct.unpack(">i", fh.read(4))
            return np.frombuffer(fh.read(length), dtype=">f4").astype(np.float32)

    def all_frames(self, variable: str) -> np.ndarray:
        """All frames of one variable: [NTIMES, NPOIN]."""
        ivar = self._var_index(variable)
        out = np.empty((self.ntimes, self.npoin), dtype=np.float32)
        with open(self.path, "rb") as fh:
            for t in range(self.ntimes):
                fh.seek(self._frame_offsets[t][ivar])
                (length,) = struct.unpack(">i", fh.read(4))
                out[t] = np.frombuffer(fh.read(length), dtype=">f4").astype(np.float32)
        return out

    def read_all(self, variables: list[str] | None = None) -> dict[str, np.ndarray]:
        variables = variables or self.variables
        return {v: self.all_frames(v) for v in variables}


def read_selafin(path: str | Path) -> Selafin:
    return Selafin(path)
