#!/usr/bin/python
# -*- coding: utf-8 -*-
import cjklib.characterlookup
import cjklib.exception
import collections

cjk = cjklib.characterlookup.CharacterLookup('C')

def MutableNamedTuple(name, fields):
  def tostr(value):
    if type(value) == unicode:
      return "'%s'" % (value.encode('utf8'))
    return repr(value)
  class TemporaryClass(object):
    __name__ = name
    def __init__(self, *args):
      assert(len(args) == len(fields))
      for (key, value) in zip(fields, args):
        self.__dict__[key] = value
    def __str__(self):
      return '%s(%s)' % (name, ', '.join(
          tostr(self.__dict__[key]) for key in fields))
  return TemporaryClass

def in_cjk_block(character):
  if not (len(character) == 1 and 0x4e00 <= ord(character) <= 0x9fff):
    print '%s is U+%s' % (character, hex(ord(character))[2:].upper())
    return False
  return True

with open('scripts/glyphs') as f:
  glyphs = f.readlines()[0].strip().decode('utf8')
  assert(all(in_cjk_block(glyph) for glyph in glyphs))
  glyph_set = set(glyphs)
assert(len(glyphs) == len(glyph_set) == 6763)

Radical = MutableNamedTuple('Radical', ['number', 'character', 'definition',
                                        'pinyin', 'traditional', 'variants'])

with open('scripts/radicals') as f:
  rows = [line[:-1].decode('utf8').split('\t') for line in f.readlines()[1:]]
  radicals = [Radical(*row) for row in rows]
assert(len(radicals) == 216)

print 'Homogenizing derived radicals:'
for radical in radicals:
  radical.number = int(radical.number)
  radical.traditional = radical.traditional or None
  radical.variants = \
    tuple(sorted(radical.variants.split(','))) if radical.variants else ()
  in_cjk_block(radical.character)
  if radical.traditional is not None:
    in_cjk_block(radical.traditional)
  [in_cjk_block(variant) for variant in radical.variants]
  assert(radical.definition)
  assert(radical.pinyin)

radical_map = dict((radical.character, radical) for radical in radicals)
assert(len(radical_map) == len(radicals))
for radical in radicals:
  if radical.traditional:
    assert(radical.traditional not in radical_map)
    radical_map[radical.traditional] = radical
  for variant in radical.variants:
    assert(variant not in radical_map), variant.encode('utf8')
    radical_map[variant] = radical
print 'Got %s radicals, including variants.' % (len(radical_map),)
radicals_used = set()

def decomposition_to_str(decomposition):
  result = ''
  for element in decomposition:
    if type(element) == unicode:
      result += element.encode('utf8')
    else:
      result += element[0].encode('utf8')
      if element[1] != 0:
        result += '[%s]' % (element[1],)
  return result

print 'Checking decompositions:'
extra_glyphs = set()
counts = collections.defaultdict(int)
decompositions = cjk.getDecompositionEntriesDict()
for glyph in glyphs:
  index = cjk.getDefaultGlyph(glyph)
  if glyph in radical_map or (glyph, index) not in decompositions:
    counts['indecomposable'] += 1
    if glyph in radical_map:
      radicals_used.add(glyph)
    continue
  decomposition = decompositions[(glyph, index)][0]
  for element in decomposition:
    if type(element) == unicode:
      continue
    (part, index) = element
    # If the index is non-zero here, the decomposition includes a variant of
    # the given part instead of the part itself. However, by inspection, the
    # few hundred or so times this occurs in the 6763 characters in GB2312 seem
    # largely benign; most of the time, the character is simply stretched
    # horizontally or vertically.
    #if index != 0:
    #  print 'In %s, got index %s for part %s' % (glyph, index, part)
    if part in radical_map:
      radicals_used.add(part)
      continue
    if part == u'？':
      counts['unknown'] += 1
      continue
    if part not in glyphs and part not in extra_glyphs:
      assert part != u'㣺'
      if cjk.isRadicalChar(part):
        try:
          equivalent_character = cjk.getRadicalFormEquivalentCharacter(part)
        except cjklib.exception.UnsupportedError:
          equivalent_character = None
        if equivalent_character in radical_map:
          if equivalent_character not in radicals_used:
            radicals_used.add(equivalent_character)
            print '(Found in %s. Equivalent character for %s: %s)' % (
                glyph, part, equivalent_character)
          continue
      if not in_cjk_block(part):
        print '(Found in %s.)' % (glyph,)
      extra_glyphs.add(part)

print counts
print '%s extra glyphs required for decompositions.' % (len(extra_glyphs),)
print '%s radicals required for decomposition.' % (len(radicals_used),)

for radical in radical_map:
  if radical not in glyphs:
    extra_glyphs.add(radical)
print 'Final list of extra glyphs:'
print ''.join(sorted(extra_glyphs))

print '\nUsed radicals:'
print ''.join(sorted(radical for radical in radical_map
                     if radical not in glyphs and
                        (radical in radicals_used or
                         radical == radical_map[radical].character)))

print '\nUnused radicals:'
print ''.join(sorted(radical for radical in radical_map
                     if not (radical in radicals_used or
                             radical == radical_map[radical].character)))
