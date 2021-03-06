# -*- coding: utf-8 -*-
# (c) 2015 Alfredo de la Fuente - AvanzOSC
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

import openerp.tests.common as common
from datetime import date


class TestMrpProductionNoSplitFinishedProductMove(common.TransactionCase):

    def setUp(self):
        super(TestMrpProductionNoSplitFinishedProductMove, self).setUp()
        self.produce_product = self.browse_ref('product.product_product_3')
        self.route_man_id = self.ref('mrp.route_warehouse0_manufacture')
        self.produce_product.write({
            'route_ids': [(6, 0, [self.route_man_id])],
        })
        self.consume_product = self.browse_ref('product.product_product_16')
        self.bom_id = self.ref('mrp.mrp_bom_8')
        self.make_procurement_model = self.env['make.procurement']
        self.procurement_model = self.env['procurement.order']
        self.procurement_rule_model = self.env['procurement.rule']
        self.produce_model = self.env['mrp.product.produce']
        self.produce_line_model = self.env['mrp.product.produce.line']
        self.workorder_produce_model = self.env['mrp.work.order.produce']
        make_procurement = self.make_procurement_model.create({
            'product_id': self.produce_product.id,
            'uom_id': self.produce_product.uom_id.id,
            'qty': 1.0,
            'date_planned': date.today(),
        })
        res = make_procurement.make_procurement()
        self.procurement = self.procurement_model.browse(res.get('res_id'))
        self.procurement.write({'bom_id': self.bom_id})
        self.procurement.run()

    def test_manufacturing_order_for_produce_product(self):
        self.assertEqual(
            len(self.procurement), 1,
            "Procurement not generated for produce product type.")
        self.assertTrue(
            bool(self.procurement.production_id),
            "MRP production no generated for procurement.")
        self.assertEqual(
            self.procurement.bom_id, self.procurement.production_id.bom_id,
            "MO must have the same BoM as in procurement.")
        self.procurement.production_id.force_production()
        produce_vals = {
            'product_qty': 5,
            'mode': 'consume_produce',
            'product_id': self.produce_product.id,
            'track_production': False,
        }
        self.produce = self.produce_model.create(produce_vals)
        produce_line_vals = {
            'product_id': self.consume_product.id,
            'product_qty': 1,
            'produce_id': self.produce.id,
            'track_production': False,
        }
        self.produce_line_model.create(produce_line_vals)
        self.produce.with_context(
            active_id=self.procurement.production_id.id).do_produce()
        self.assertEqual(
            len(self.procurement.production_id.move_created_ids2), 1,
            "It has created more than one product to produce movement.")

    def test_workorder_do_produce_consume_for_produce_product(self):
        self.procurement.production_id.force_production()
        for workorder in self.procurement.production_id.workcenter_lines:
            consume = self.workorder_produce_model.with_context(
                active_ids=[workorder.id], active_id=workorder.id).create({
                    'mode': 'consume_produce',
                    'product_qty': 5,
                })
            consume.do_consume_produce()
        self.assertEqual(
            len(self.procurement.production_id.move_created_ids2), 1,
            "It has created more than one product to produce movement.")
