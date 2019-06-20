#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for VolumeGeometry."""


import unittest
import numpy as np
import tomosipo as ts
import astra


class TestVolumeGeometry(unittest.TestCase):
    """Tests for VolumeGeometry."""

    def setUp(self):
        """Set up test fixtures, if any."""
        pass

    def tearDown(self):
        """Tear down test fixtures, if any."""
        pass

    def test_is_volume_geometry(self):
        self.assertTrue(ts.is_volume_geometry(ts.VolumeGeometry()))
        self.assertFalse(ts.is_volume_geometry(ts.cone()))
        self.assertFalse(ts.is_volume_geometry(None))

    def test_init(self):
        """Test init."""
        vg = ts.VolumeGeometry()

    def test_equal(self):
        """Test __eq__

        """

        vg = ts.volume()
        unequal = [ts.volume(shape=10), ts.volume(shape=(10, 9, 8)), ts.cone()]

        self.assertEqual(vg, vg)

        for u in unequal:
            self.assertNotEqual(vg, u)

    def test_volume(self):
        self.assertEqual(ts.volume(), ts.VolumeGeometry())
        shapes = [2, (1, 4, 5), (10, 10, 10)]
        for s in shapes:
            self.assertEqual(ts.volume(s), ts.VolumeGeometry().reshape(s))

    def test_astra(self):
        vg = ts.VolumeGeometry()
        vg = vg.scale((1, 2, 3)).translate((10, 20, 30))
        vg1 = ts.VolumeGeometry.from_astra(vg.to_astra())

        self.assertEqual(vg, vg1)

    def test_translate(self):
        vg = ts.VolumeGeometry()

        self.assertEqual(vg, vg.translate((0, 0, 0)))
        self.assertEqual(vg, vg.translate(0))
        self.assertEqual(vg, vg.untranslate((0, 0, 0)))
        self.assertEqual(vg, vg.untranslate(0))
        for _ in range(10):
            t = np.random.normal(size=3)
            self.assertAlmostEqual(vg, vg.translate(t).untranslate(t))

    def test_scale(self):
        vg = ts.VolumeGeometry()

        self.assertEqual(vg, vg.scale((1, 1, 1)))
        self.assertEqual(vg, vg.scale(1))
        for _ in range(10):
            t = abs(np.random.normal(size=3)) + 0.01
            self.assertAlmostEqual(vg, vg.scale(t).scale(1 / t), places=5)

    def test_multiply(self):
        vg = ts.VolumeGeometry()
        self.assertEqual(vg, vg.multiply((1, 1, 1)))
        self.assertEqual(vg, vg.multiply(1))
        for _ in range(10):
            t = abs(np.random.normal(size=3)) + 0.01
            self.assertAlmostEqual(vg, vg.multiply(t).multiply(1 / t), places=5)

    def test_contains(self):
        vg = ts.VolumeGeometry()
        self.assertFalse(vg in vg.translate(1))
        self.assertFalse(vg in vg.scale(0.5))
        self.assertTrue(vg in vg.scale(2))
        self.assertTrue(vg.translate(5) in vg.translate(5).scale(2))
        self.assertTrue(vg in vg)

    def test_intersection(self):

        vg = ts.VolumeGeometry()

        for _ in range(100):
            t = np.random.normal(size=3)
            r = np.random.normal(size=3)
            r = abs(r) + 0.01

            vg2 = vg.translate(t).scale(r)

            intersection = vg.intersect(vg2)

            if intersection is not None:
                self.assertTrue(intersection in vg)
                self.assertTrue(intersection in vg2)
            else:
                self.assertFalse(vg in vg2)
                self.assertFalse(vg2 in vg)

            self.assertAlmostEqual(vg2, vg2.intersect(vg2))

    def test_reshape(self):
        vg = ts.VolumeGeometry()

        vg1 = vg.reshape(100)
        vg2 = vg.reshape((100,) * 3)

        self.assertEqual(vg1, vg2)

    def test_to_box(self):
        vg = ts.volume(shape=(3, 5, 7))
        box = vg.to_box()

        self.assertAlmostEqual(box.size, vg.size())
        # XXX: Really do not know what to test here..

    def test_volume_from_projection(self):
        """Test volume_from_projection_geometry

        This method checks that astra projections of a volume obtained
        by volume_from_projection_geometry satisfy some
        conditions. Notably,

        1) when inside=True, the backprojection of a detector
           should hit all volume voxels. This should actually hold for
           each angle individually, but this is too expensive to test.
        2) when inside=False, the forward projection of the volume
           should hit each detector pixel. Again, this should hold for
           each angle individually.

        NOTE: When the source intersects the volume, astra does not
        always do a correct forward projection. Hence, a correctly
        sized volume might fail the test.

        """
        num_angles = 119
        proj_angles = np.linspace(0, 2 * np.pi, num_angles, False)

        # Test with various parameters. Set interactive to True, to
        # see them in action.
        params = [
            [(0.5, 0.2), (8, 20), 200, 20],
            [(1.0, 1.0), (8, 20), 17, 0],
            [(1.0, 1.0), (8, 20), 8, 19],
            [(1.0, 1.0), (20, 8), 10, 100],
            [(1.0, 1.0), (8, 20), 100, 10],
            [(1.0, 1.0), (8, 20), 8, 20],
            [(1.0, 1.0), (20, 8), 10, 0],
        ]

        for (d_spacing, num_pixels, src_dist, det_dist) in params:
            pg = astra.create_proj_geom(
                "cone", *d_spacing, *num_pixels, proj_angles, src_dist, det_dist
            )
            pg = ts.from_astra_geometry(pg)
            vg = ts.volume_from_projection_geometry(pg, inside=True)
            with ts.data(vg) as vd, ts.data(pg) as pd:
                pd.data[:] = 1.0
                ts.backward(vd, pd)
                self.assertGreater(
                    np.min(np.abs(vd.data)),
                    0,
                    msg=f"Backward failed: {(num_pixels, src_dist, det_dist)}",
                )
            vg = ts.volume_from_projection_geometry(pg, inside=False)
            with ts.data(vg) as vd, ts.data(pg) as pd:
                vd.data[:] = 1.0
                ts.forward(vd, pd)
                # ts.display(pd)
                # ts.display(pg, vg)
                self.assertGreater(
                    np.min(np.abs(pd.data)),
                    0,
                    msg=f"Forward failed: {(num_pixels, src_dist, det_dist)}",
                )
