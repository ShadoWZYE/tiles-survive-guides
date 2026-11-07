"""Selected static Raid counter rules, for attribution tests; not an engine simulator."""
import math

def number(value):
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):raise ValueError('Finite numeric event value required')
    return value

def owner(guid,entities,registered):
    if guid in registered:return guid
    entity=entities.get(guid)
    if not entity or entity.get('camp')!=0:return None
    if entity.get('kind')=='soldier':host=entity.get('follow_hero')
    elif entity.get('kind')=='summon' and entity.get('template_present') is True and entity.get('is_not_statistics')!=1:host=entity.get('host')
    else:return None
    return host if host in registered else None

def ledger(events,entities,registered):
    counters={g:{'damage':0.,'damage_taken':0.,'healing':0.,'healing_received':0.,'hp_change_damage':0.,'shield_absorbed':0.} for g in registered}
    mechanisms={};unattributed={'outgoing_damage':0.,'incoming_damage':0.,'outgoing_healing':0.,'incoming_healing':0.};ignored=0
    for event in events:
        kind=event['kind']
        if kind=='hp_change':
            value=number(event['hp_change'])
            if event.get('effect_is_not_statistics')==1:ignored+=1;continue
            damage=value<0;amount=abs(value);channel='hp_change_damage' if damage else 'healing'
        elif kind=='shield_absorb':
            amount=number(event['amount'])
            if amount<0:raise ValueError('Negative shield absorption')
            damage=True;channel='shield_absorbed'
        else:raise ValueError('Unsupported statistics callback')
        source=owner(event.get('source'),entities,registered);target=owner(event.get('target'),entities,registered)
        if source is not None:
            counters[source]['damage' if damage else 'healing']+=amount
            if damage:counters[source][channel]+=amount
        else:unattributed['outgoing_damage' if damage else 'outgoing_healing']+=amount
        if target is not None:counters[target]['damage_taken' if damage else 'healing_received']+=amount
        else:unattributed['incoming_damage' if damage else 'incoming_healing']+=amount
        mechanism=event.get('mechanism','unknown')
        bucket=mechanisms.setdefault(mechanism,{'hp_change_damage':0.,'shield_absorbed':0.,'healing':0.});bucket[channel]+=amount
    return {'owners':counters,'mechanisms':mechanisms,'unattributed':unattributed,'ignored_hp_change_events':ignored,'scope':'Synthetic callback ledger following selected static methods; event stream and mechanism labels must be supplied independently. Damage includes shield absorption and is not HP removed.'}
