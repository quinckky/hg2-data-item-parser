import csv
import re

import requests

from constants import (CATEGORY_NAMES, DAMAGE_TYPE_NAMES, SKILL_NAMES,
                       IMAGES_URL, TEXTMAP_NAMES, WEAPON_TYPE_NAMES)

_textmap_new: dict = requests.get(TEXTMAP_NAMES['textmap_new']).json()


def _get_row(file_path: str, column_name: str, column_value: str | int | float) -> dict | None:
    with open(file_path, 'r', newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file, delimiter="\t")
        for row in reader:
            if str(row[column_name]) == str(column_value):
                return row
    return None


def _get_text(id_: int) -> str:
    if str(id_) in _textmap_new.keys():
        text = _textmap_new[str(id_)]
    else:
        textmap_old = _get_row(
            'data/'+TEXTMAP_NAMES['textmap_old'], 'TEXT_ID', id_)
        text = textmap_old['EN'] if textmap_old is not None else 'TEXT'

    return text


def _get_category(id_: int) -> tuple:
    for category_name, filename in CATEGORY_NAMES.items():

        category = _get_row('data/JP/'+filename, 'DisplayNumber', id_)
        if category is not None:
            return 'JP', category_name, category

        category = _get_row('data/CN/'+filename, 'DisplayNumber', id_)
        if category is not None:
            return 'CN', category_name, category

    return None, None, None


def get_main_info(id_: int) -> dict | None:
    main_info = dict()
    _, _, category = _get_category(id_)
    if category is None:
        return None

    main_info['ID'] = category['ID']
    main_info['Number'] = id_
    main_info['Title ID'] = int(category['DisplayTitle'])
    main_info['Title'] = _get_text(main_info['Title ID'])
    image_id = int(category['DisplayImage'])
    trailing_zero = '0' * max(0, 2 - len(str(image_id)))

    # Can use allequipmenticons AssetBundle instead, but sometimes items in it don't have background
    main_info['Icon'] = f'{IMAGES_URL}{trailing_zero}{image_id}.png'
    main_info['Rarity'] = int(category['Rarity'])
    main_info['Damage Type'] = DAMAGE_TYPE_NAMES[category.get(
        'DamageType', 'none')]

    return main_info


def get_properties(id_: int) -> dict | None:
    properties = dict()
    _, category_name, category = _get_category(id_)
    if category is None:
        return None

    max_lvl = properties['Max Lvl'] = int(category['MaxLv'])

    if category_name != 'pet':
        properties['Carry Load'] = int(category['Cost'])

    if category_name in ['costume', 'weapon']:
        properties['Max Lvl HP'] = round(
            float(category['HPBase']) + float(category['HPAdd']) * (max_lvl - 1))

    if category_name == 'weapon':
        properties['Type'] = WEAPON_TYPE_NAMES[category['BaseType']]
        properties['Max Lvl Damage'] = round(
            float(category['DamageBase']) + float(category['DamageAdd']) * (max_lvl - 1))
        properties['Max Lvl Ammo'] = round(
            float(category['AmmoBase']) + float(category['AmmoAdd']) * (max_lvl - 1))
        if properties['Max Lvl Ammo'] == -1:
            properties['Max Lvl Ammo'] = '∞'
        properties['Max Lvl ASPD'] = round(float(
            category['FireRateBase']) + float(category['FireRateAdd']) * (max_lvl - 1), 3)
        properties['Deploy Limit'] = int(category['LimitedNumber'])
        properties['Duration'] = round(float(
            category['CountDownTime']) + float(category['CountDownTimeAdd']) * (max_lvl - 1), 2)
        properties['Crit Rate'] = int(float(category['CriticalRate']) * 100)

    if category_name == 'pet':
        properties['Max Lvl Damage'] = round(
            float(category['Attack']) + float(category['Attack_Add']) * (max_lvl - 1))
        properties['Crit Rate'] = int(float(category['initCritRate']) * 100)
        properties['Base Sync'] = int(category['SynInit'])
        properties['Max Sync'] = int(
            category['SynInit']) + int(category['SynAdd']) * int(category['SynMaxLevel'])

    properties = {key: value for key,
                  value in properties.items() if value != 0}

    return properties


def get_skills(id_: int) -> list | None:
    skills = []
    server, category_name, category = _get_category(id_)
    if category is None:
        return None

    max_lvl = int(category['MaxLv'])

    if category_name != 'pet':
        num = int(category['NumProps'])
        skills_id = [int(category[f'Prop{i}id']) for i in range(1, num + 1)]

        for skill_id in skills_id[:]:
            skill = _get_row('data/'+server+'/' +
                             SKILL_NAMES['item_skills'], 'ID', skill_id)

            if skill is not None and skill['DisplayTitle'] != '0':
                skills.append(skill)
            else:
                skills_id.remove(skill_id)
                num -= 1

        damage_types = [DAMAGE_TYPE_NAMES[skill['Feature']]
                        for skill in skills]
        titles_id = [int(skill['DisplayTitle'][4:]) for skill in skills]
        descriptions_id = [int(skill['DisplayDescription'][4:])
                           for skill in skills]

        max_lvl_values = [[float(category[f'Prop{i}Param{j}']) + float(category[f'Prop{i}Param{j}Add']) * (
            max_lvl - 1) for j in range(1, 6)] for i in range(1, num + 1)]
        max_break_values = []

        for i, skill in enumerate(skills):
            slots_num = int(skill['SlotCount'])
            slots_equip = [skill[f'Slot{j}Equips']
                           for j in range(1, slots_num + 1)]

            for used_slot, slot_equip in enumerate(slots_equip, start=1):
                if str(id_) in slot_equip.split(';'):
                    break
            else:
                used_slot = 1

            max_break_values.append([max_lvl_values[i][j-1] + float(skill[f'Slot{used_slot}MaxLevel']) * float(
                skill[f'Slot{used_slot}Para{j}Add']) for j in range(1, 6)])

    else:
        num = 4
        skills_id = [int(category['UltraSkillid']), int(category['HiddenUltraSkillid']), int(
            category['normalSkill1Id']), int(category['normalSkill2Id'])]

        for skill_id in skills_id:
            skill = _get_row('data/'+server+'/' +
                             SKILL_NAMES['pet_skills'], 'ID', skill_id)
            skills.append(skill)

        damage_types = [None for _ in range(num)]
        titles_id = [int(skill['DisplayTitle']) for skill in skills]
        descriptions_id = [int(skill['DisplayDescription'])
                           for skill in skills]
        max_lvl_values = [
            [float(skill[f'Para{j}']) for j in range(1, 7)] for skill in skills]
        max_break_values = [[max_lvl_values[i][j-1] + int(skill[f'Maxlevel']) * float(
            skill[f'Para{j}SkillUpAdd']) for j in range(1, 7)] for i, skill in enumerate(skills)]

    titles = [_get_text(title_id) for title_id in titles_id]
    descriptions = [_get_text(description_id)
                    for description_id in descriptions_id]

    for i, description in enumerate(descriptions):

        description = re.sub(r'# ?!?ALB ?\(\d+\)', '', description)
        description = description.replace('#n', '')
        description = description.replace(' %', '%')

        for j, max_lvl_value, max_break_value in zip(range(1, 7), max_lvl_values[i], max_break_values[i]):

            if f'#{j}%' in description:
                max_lvl_value *= 100
                max_break_value *= 100

            match = re.search(fr'([1-9]+)#{j}', description)
            if match is not None:
                mul = int(match.group(1))
                max_lvl_value *= mul
                max_break_value *= mul
            else:
                mul = ''

            if max_lvl_value != max_break_value:
                replacement = f'{max_lvl_value:g}({max_break_value:g})'
            else:
                replacement = f'{max_lvl_value:g}'

            description = description.replace(f'{mul}#{j}', replacement)

        descriptions[i] = description.strip()

    return [(skill_id, damage_type, title_id, title, description_id, description)
            for skill_id, damage_type, title_id, title, description_id, description
            in zip(skills_id, damage_types, titles_id, titles, descriptions_id, descriptions)]
