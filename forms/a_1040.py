#! /usr/bin/python
#    Copyright (C) 2019 pyTaxPrep
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.
'''
Fills in a Schedule A form.

Relies on portions of the Form 1040 (up to the line computing AGI).
Additionally, you must define the following keys in data.json:
    => name
    => ssn
    => w2 (specifically the 'state_withheld' key)

Optionally, you can define
    => medical_expenses
    => donations_cash
    => donations_noncash
    => state_due_last_year
    => estimated_state

Currently, the following lines are filled:
    => Medical and Dental Expenses (1-4)
    => State and Local Income Taxes (5a, 5d, 5e, and 7) but
       not real estate taxes, personal property taxes (5b or 5c),
       or 'other' taxes (6). 
    => Gifts to charity (11 - 12, 14) but not carryovers (13).
    => Total line (17)

'''

from . import utils
from . import configs
from . import constants

from . import s_1040

###################################

def build_data():

    info = utils.parse_values()

    data_dict = {
        'name' : info['name'],
        'ssn'  : info['ssn']
    }

    filing_status = info['filing_status'] if 'filing_status' in info else "single"

    form_1040 = s_1040.build_data(short_circuit='AGI')

    # Medical expenses
    medical_expenses = info['medical_expenses'] if 'medical_expenses' in info else 0
    utils.add_keyed_float(medical_expenses, 'medical_exp', data_dict)
        
    agi = utils.dollars_cents_to_float(form_1040['adjusted_gross_income_dollars'],
                                       form_1040['adjusted_gross_income_cents'])
    utils.add_keyed_float(agi, 'form_1040_line_7', data_dict)

    nondeductible_medical_exp = agi * constants.get_value("NONDEDUCTIBLE_MEDICAL_EXPENSE_RATE")
    utils.add_keyed_float(nondeductible_medical_exp, 'nondeductible_medical_exp', data_dict)

    qualified_medical_exp = max(0, medical_expenses - nondeductible_medical_exp)
    utils.add_keyed_float(qualified_medical_exp, 'qualified_medical_exp', data_dict)

    # State and Local Tax = 
    #   1) Amount paid this year on last year's return
    #   2) Estimated payments for this year
    #   3) Withheld taxes on w2
    state_local = 0.0
    if 'state_due_last_year' in info:
        state_local += info['state_due_last_year']
    if 'estimated_state' in info:
        state_local += sum([x['amount'] for x in info['estimated_state'] if x['date'].startswith(configs.get_value("tax_year"))])
    state_local += sum([x['state_withheld'] for x in info['w2']])

    utils.add_keyed_float(state_local, 'income_sales_tax', data_dict)

    total_state_local = utils.add_fields(data_dict, ['income_sales_tax',
                                                     'real_estate_taxes',
                                                     'property_taxes'])
    
    utils.add_keyed_float(total_state_local, 'total_state_local', data_dict)

    max_deductible_state_tax = constants.get_value("MAX_DEDUCTIBLE_STATE_TAX", filing_status)
    floor = min(total_state_local, max_deductible_state_tax)
    utils.add_keyed_float(floor, 'floor_taxes', data_dict)
    
    total_taxes = floor
    utils.add_keyed_float(total_taxes, 'total_taxes', data_dict)

    # Home mortgage interest
    home_interest = utils.add_fields(data_dict, ['home_mortgage_loan_interest',
                                                 'home_mortgage_not_1098',
                                                 'points_not_1098'])

    utils.add_keyed_float(home_interest, 'total_home_interest', data_dict)

    # Total interest
    total_interest = home_interest
    utils.add_keyed_float(total_interest, 'total_interest', data_dict)

    # Charity donations
    if 'donations_cash' in info:
        charity_monies = sum([x['amount'] for x in info['donations_cash']])
        utils.add_keyed_float(charity_monies, 'charity_monies', data_dict)

    if 'donations_noncash' in info:
        charity_others = sum([x['amount'] for x in info['donations_noncash']])
        utils.add_keyed_float(charity_others, 'charity_others', data_dict)
        
    charity_total = utils.add_fields(data_dict, ['charity_monies',
                                           'charity_others',
                                           'charity_carryover'])
    utils.add_keyed_float(charity_total, 'charity_total', data_dict)

    # Sum itemized deductions
    total_deductions = utils.add_fields(data_dict, ['qualified_medical_expenses',
                                                    'total_taxes',
                                                    'total_interest',
                                                    'charity_total',
                                                    'casualty_theft_losses',
                                                    'other_itemized'])
    utils.add_keyed_float(total_deductions, 'total_itemized', data_dict)

    return data_dict

def fill_in_form():
    data_dict = build_data()
    basename = 'f1040sa.pdf'
    return utils.write_fillable_pdf(basename, data_dict, 'sa.keys')


if __name__ == '__main__':
    fill_in_form()



