import csv
import re

import requests
from typing_extensions import Literal

from constants import (CATEGORY_NAMES, DAMAGE_TYPE_NAMES, SKILL_NAMES,
                       TEXTMAP_NAMES, WEAPON_TYPE_NAMES)

textmap_new: dict = requests.get(TEXTMAP_NAMES['textmap_new']).json()


def get_text(id_: int) -> str:
    text_old = get_row_by_column_value('data/'+TEXTMAP_NAMES['textmap_old'], 'TEXT_ID', id_)
    #return text_old['EN' | 'JP' | 'CN'] for original text
    
    text = textmap_new.get(str(id_), text_old['EN'] if text_old else 'TEXT')
    return text


def get_row_by_column_value(file_path: str, column_name: str, column_value: str | int | float) -> dict | None:
    with open(file_path, 'r', newline="", encoding='utf-8') as file:
        reader = csv.DictReader(file, delimiter="\t")
        for row in reader:
            if str(row[column_name]) == str(column_value):
                return row
    return None


def get_category(id_: int) -> tuple[Literal['JP', 'CN'], Literal['weapon', 'costume', 'badge', 'pet'], dict] | tuple[None, None, None]:
    for name, filename in CATEGORY_NAMES.items():
        category_cn = get_row_by_column_value('data/CN/'+filename, 'DisplayNumber', id_)
        category_jp = get_row_by_column_value('data/JP/'+filename, 'DisplayNumber', id_)
        
        #JP prority; swap to CN priority
        if category_jp:
            return 'JP', name[:-1], category_jp

        if category_cn:
            return 'CN', name[:-1], category_cn

    return None, None, None


def get_main_info(id_: int) -> dict | None:
    main_info = dict()
    _, category_name, category = get_category(id_)
    if not category:
        return None
    
    main_info['ID'] = category['ID']
    main_info['Number'] = id_
    main_info['Title ID'] = int(category['DisplayTitle'])
    main_info['Title'] = get_text(main_info['Title ID'])
    image_id = int(category['DisplayImage'])
    
    #You can use allequipmenticons AssetBundle instead, but sometimes items in it doesn't have background
    main_info['Icon'] = f'http://static.image.mihoyo.com/hsod2_webview/images/broadcast_top/equip_icon/png/{image_id}.png'
    main_info['Rarity'] = int(category['Rarity'])
    main_info['Damage Type'] = DAMAGE_TYPE_NAMES[category['DamageType']] if category_name == 'weapon' else None
    
    return main_info


def get_properties(id_: int) -> dict | None:
    properties = dict()
    _, category_name, category = get_category(id_)
    if not category:
        return None
    
    max_lvl = properties['Max Lvl'] = int(category['MaxLv'])

    if category_name != 'pet':
        properties['Carry Load'] = int(category['Cost'])
        
    if category_name in ['costume', 'weapon']:
        properties['Max Lvl HP'] = round(float(category['HPBase']) + float(category['HPAdd']) * (max_lvl - 1))
    
    if category_name == 'weapon':
        properties['Type'] = WEAPON_TYPE_NAMES[category['BaseType']]
        properties['Max Lvl Damage'] = round(float(category['DamageBase']) + float(category['DamageAdd']) * (max_lvl - 1))
        properties['Max Lvl Ammo'] = round(float(category['AmmoBase']) + float(category['AmmoAdd']) * (max_lvl - 1))
        if properties['Max Lvl Ammo'] == -1: 
            properties['Max Lvl Ammo'] = '∞'
        properties['Max Lvl ASPD'] = round(float(category['FireRateBase']) + float(category['FireRateAdd']) * (max_lvl - 1), 3)
        properties['Deploy Upper Limit'] = int(category['LimitedNumber'])
        properties['Duration'] = round(float(category['CountDownTime']) + float(category['CountDownTimeAdd']) * (max_lvl - 1), 2)
        properties['Crit Rate'] = round(float(category['CriticalRate']) * 100, 2)
        if properties['Crit Rate'] == int(properties['Crit Rate']): 
            properties['Crit Rate'] = int(properties['Crit Rate'])
        
    if category_name == 'pet':
        properties['Max Lvl Damage'] = round(float(category['Attack']) + float(category['Attack_Add']) * (max_lvl - 1))
        properties['Crit Rate'] = round(float(category['initCritRate']) * 100, 2)
        if properties['Crit Rate'] == int(properties['Crit Rate']): 
            properties['Crit Rate'] = int(properties['Crit Rate'])
        properties['Base Sync'] = int(category['SynInit'])
        properties['Max Sync'] = int(category['SynInit']) + int(category['SynAdd']) * int(category['SynMaxLevel'])
        
    properties = {key : value for key, value in properties.items() if value != 0}
    return properties


def get_skills(id_: int) -> list[tuple[Literal['Physical', 'Fire', 'Ice', 'Energy', 'Light', 'Poison'] | None, int, str, int, str]] | None:
    skills = []
    server, category_name, category = get_category(id_)
    if not category:
        return None
    
    max_lvl = int(category['MaxLv'])
    
    if category_name != 'pet':
        num = int(category['NumProps'])
        skills_id = [int(category[f'Prop{i}id']) for i in range(1, num + 1)]

        for skill_id in skills_id:
            skill = get_row_by_column_value(f'data/{server}/'+SKILL_NAMES['item_skills'], 'ID', skill_id)
            
            #Mihoyo be like: why not add non-existent or useless skills as well? 
            if skill and skill['DisplayTitle'] != '0':
                skills.append(skill)
            else:
                skills_id.remove(skill_id)
                num -= 1

        damage_types = [DAMAGE_TYPE_NAMES[skill['Feature']] for skill in skills]
        titles_id = [int(skill['DisplayTitle'].replace('TEXT', '')) for skill in skills]
        descriptions_id = [int(skill['DisplayDescription'].replace('TEXT', '')) for skill in skills]
        
        max_lvl_values = [[float(category[f'Prop{i}Param{j}']) + float(category[f'Prop{i}Param{j}Add']) * (max_lvl - 1) for j in range(1, 6)] for i in range(1, num + 1)]
        max_break_values = []
        
        for i, skill in enumerate(skills):
            slots_num = int(skill['SlotCount'])
            slots_equip = [skill[f'Slot{j}Equips'] for j in range(1, slots_num + 1)]
            
            for used_slot, slot_equip in enumerate(slots_equip, start=1):
                if str(id_) in slot_equip.split(';'):
                    break
            else:
                used_slot = 1
                
            max_break_values.append([max_lvl_values[i][j-1] + float(skill[f'Slot{used_slot}MaxLevel']) * float(skill[f'Slot{used_slot}Para{j}Add']) for j in range(1, 6)])
            
    else:
        num = 4
        skills_id = [int(category['UltraSkillid']), int(category['HiddenUltraSkillid']), int(category['normalSkill1Id']), int(category['normalSkill2Id'])]
        
        for skill_id in skills_id:
            skill = get_row_by_column_value(f'data/{server}/'+SKILL_NAMES['pet_skills'], 'ID', skill_id)
            skills.append(skill)
        
        damage_types = [None for _ in range(num)]
        titles_id = [int(skill['DisplayTitle']) for skill in skills]
        descriptions_id = [int(skill['DisplayDescription']) for skill in skills]
        
        max_lvl_values = [[float(skill[f'Para{j}']) for j in range(1, 7)] for skill in skills]
        max_break_values = [[max_lvl_values[i][j-1] + int(skill[f'Maxlevel']) * float(skill[f'Para{j}SkillUpAdd']) for j in range(1, 7)] for i, skill in enumerate(skills)]
    
    titles = [get_text(title_id) for title_id in titles_id]
    descriptions = [get_text(description_id) for description_id in descriptions_id]

    for i, description in enumerate(descriptions):
        
        #Delete this ALB at the beginning, idk what is this
        description = re.sub(r'# ?!?ALB ?\(\d+\)', '', description)
        
        #Delete unnecessary \n and space before %
        description = description.replace('#n', '')
        description = description.replace(' %', '%')   
        
        for j, max_lvl_value, max_break_value in zip(range(1, 7), max_lvl_values[i], max_break_values[i]):
            
            #Replace 0.01 with 1%
            if re.search(fr'#{j} ?%', description):
                max_lvl_value *= 100
                max_break_value *= 100
            
            #Mihoyo math: put a two in front of a number and it's a multiplication of that number by 2!
            if re.search(fr'2#{j}', description):
                max_lvl_value *= 2
                max_break_value *= 2
                
            #Avoiding situations like .0000003 and .0
            max_lvl_value = round(max_lvl_value, 4)
            if max_lvl_value == int(max_lvl_value): 
                max_lvl_value = int(max_lvl_value)
                
            max_break_value = round(max_break_value, 4)
            if max_break_value == int(max_break_value): 
                max_break_value = int(max_break_value)

            replacement = fr'{max_lvl_value}({max_break_value})' if max_lvl_value != max_break_value else str(max_lvl_value)
            description = re.sub(fr'2?#{j}', replacement, description)
            
        descriptions[i] = description.strip()
    
    return [(skill_id, damage_type, title_id, title, description_id, description) for skill_id, damage_type, title_id, title, description_id, description in zip(skills_id, damage_types, titles_id, titles, descriptions_id, descriptions)]


#UTF-8 encode required sometimes
def check_item(id_: int) -> None:
    main_info = get_main_info(id_)
    if not main_info:
        print(f'No.{id_} not found')
    properties = get_properties(id_)
    skills = get_skills(id_)
    print(f'{main_info}\n{properties}')
    for skill in skills:
        print(skill)


if __name__ == '__main__':
    print('Start')
    for id_ in range(3000, 3010):
        check_item(id_)
    print('End')
    