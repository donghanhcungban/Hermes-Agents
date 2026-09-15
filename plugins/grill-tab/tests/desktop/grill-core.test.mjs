import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

import { fallbackBrief, initialGrillState, reduceGrill, shouldStartFromTab } from '../../desktop/grill-core.mjs'

test('state machine advances idle → asking → active → done → briefing → preview → idle', () => {
  let state = initialGrillState()
  state = reduceGrill(state, { type: 'START', intent: 'Ship a plugin' })
  assert.equal(state.status, 'asking')
  assert.equal(state.intent, 'Ship a plugin')

  state = reduceGrill(state, {
    type: 'INTERROGATION',
    response: { category: 'goal', done: false, options: ['A'], question: 'What outcome matters?', recommended: 'A usable plugin' }
  })
  assert.equal(state.status, 'active')
  assert.equal(state.current.question, 'What outcome matters?')

  state = reduceGrill(state, { type: 'COMMIT_ANSWER', answer: '' })
  assert.equal(state.status, 'asking')
  assert.deepEqual(state.ladder, [
    { answer: 'A usable plugin', category: 'goal', question: 'What outcome matters?', recommended: 'A usable plugin', settledFromRecommendation: false }
  ])

  state = reduceGrill(state, { type: 'INTERROGATION', response: { done: true, reason: 'Nothing critical left.' } })
  assert.equal(state.status, 'done')

  state = reduceGrill(state, { type: 'WRITE_BRIEF' })
  assert.equal(state.status, 'briefing')
  state = reduceGrill(state, { type: 'BRIEF_READY', brief: '## Goal\nShip it' })
  assert.equal(state.status, 'finalized')
  assert.equal(state.finalized, true)
  assert.equal(state.brief, '## Goal\nShip it')
  state = reduceGrill(state, { type: 'ESC' })
  assert.equal(state.status, 'finalized')
  state = reduceGrill(state, { type: 'RESET' })
  assert.equal(state.status, 'idle')
})

test('Esc, Bacg, category: 'scope', question: 'Where?', recommended: 'Desktop only', settledFromRecommendation: true }
  const state = {
    ...initialGrillState(),
    current: { category: 'goal', options: [], question: 'What outcome?', recommended: 'A usable plugin' },
    ladder: [
      { answer: 'Original goal', category: 'goal', question: 'What outcome?', recommended: 'A usable plugin', settledFromRecommendation: true },
      later
    ],
    status: 'active'
  }

  const editing = reduceGrill(state, { type: 'START_EDIT_CHECKPOINT', index: 0 })
  assert.equal(editing.editingIndex, 0)
  assert.deepEqual(editing.ladder, state.ladder)

  const saved = reduceGrill(editing, { type: 'SAVE_CHECKPOINT', index: 0, answer: 'Updated goal' })
  assert.equal(saved.editingIndex, null)
  assert.deepEqual(saved.ladder, [
    { ...state.ladder[0], answer: 'Updated goal', settledFromRecommendation: false },
    later
  ])
  assert.deepEqual(saved.ladder[1], later)
})

test('removing a checkpoint preserves every other rung and adjusts an active edit index', () => {
  const ladder = [
    { answer: 'One', category: 'a', question: 'Q1', recommended: 'R1', settledFromRecommendation: false },
    { answer: 'Two', category: 'b', question: 'Q2', recommended: 'R2', settledFromRecommendation: false },
    { answer: 'Three', category: 'c', question: 'Q3', recommended: 'R3', settledFromRecommendation: false }
  ]
  const state = { ...initialGrillState(), ladder, editingIndex: 2, status: 'done' }
  const removed = reduceGrill(state, { type: 'REMOVE_CHECKPOINT', index: 0 })
  assert.deepEqual(removed.ladder, [ladder[1], ladder[2]])
  assert.equal(removed.editingIndex, 1)

  const removedEditing = reduceGrill(removed, { type: 'REMOVE_CHECKPOINT', index: 1 })
  assert.deepEqual(removedEditing.ladder, [ladder[1]])
  assert.equal(removedEditing.editingIndex, null)
})

test('checkpoint edits are blocked while briefing or after finalization', () => {
  const rung = { answer: 'Keep', category: 'goal', question: 'Q', recommended: 'R', settledFromRecommendation: false }
  for (const state of [
    { ...initialGrillState(), ladder: [rung], status: 'briefing' },
    { ...initialGrillState(), ladder: [rung], status: 'finalized', finalized: true },
    { ...initialGrillState(), ladder: [rung], status: 'done', finalized: true }
  ]) {
    const started = reduceGrill(state, { type: 'START_EDIT_CHECKPOINT', index: 0 })
    const saved = reduceGrill(state, { type: 'SAVE_CHECKPOINT', index: 0, answer: 'Changed' })
    const removed = reduceGrill(state6W26��6VB�7vW'2r�������6��7B�FFW"�����7vW#�t�2r�6FVv�'��vr�VW7F���ur�&V6���V�FVC�u#r�6WGF�VDg&��&V6���V�FF���f�6R�����7vW#�t�2"r�6FVv�'��v"r�VW7F���u"r�&V6���V�FVC�u#"r�6WGF�VDg&��&V6���V�FF���f�6R�����7vW#�t�22r�6FVv�'��v2r�VW7F���u2r�&V6���V�FVC�u#2r�6WGF�VDg&��&V6���V�FF���f�6RТТ6��7B7FFR�������F��w&���7FFR�����7vW#�rr��7W'&V�C��6FVv�'��vBr��F���3����VW7F���uC�r�&V6���V�FVC�u#BFVfV�Br����FFW"��7FGW3�v7F�fRp�Р���W6W"��G2V�FW"v�F��WB�7vW&��rVW7F���@�6��7B'&�Vf��r�&VGV6Tw&��7FFR��G�S�uu$�DU�%$�Tbr��7vW#�rr���6�VFT7W'&V�C�G'VRҐ�76W'B�WV'&�Vf��r�7FGW2�v'&�Vf��rr��76W'B�WV'&�Vf��r�7W'&V�B��V��76W'B�WV'&�Vf��r��FFW"��V�wF��2�t�FFW"�W7B��ǒ6��F��F�R26��6VB�7vW'2���BFVfV�F��rBr��76W'B�FVWWV'&�Vf��r��FFW"��FFW"��Ґ��FW7B�uu$�DU�%$�Tb��7F�fRVW7F���v�F�W�Ɩ6�B�7vW"6��֗G2F�B�7vW"r�������6��7B�FFW"�����7vW#�t�2r�6FVv�'��vr�VW7F���ur�&V6���V�FVC�u#r�6WGF�VDg&��&V6���V�FF���f�6RТТ6��7B7FFR�������F��w&���7FFR�����7vW#�tW�Ɩ6�B"r��7W'&V�C��6FVv�'��v"r��F���3����VW7F���u#�r�&V6���V�FVC�u#"FVfV�Br����FFW"��7FGW3�v7F�fRp�Р�6��7B'&�Vf��r�&VGV6Tw&��7FFR��G�S�uu$�DU�%$�Tbr��7vW#�tW�Ɩ6�B"r���6�VFT7W'&V�C�G'VRҐ�76W'B�WV'&�Vf��r�7FGW2�v'&�Vf��rr��76W'B�WV'&�Vf��r��FFW"��V�wF��"��76W'B�WV'&�Vf��r��FFW%����7vW"�tW�Ɩ6�B"r��Ґ��FW7B�vV�B�F��V�Bf��s�6�V6����BVF�B�WF��6fR�&V��fR��FW"�7vW"&W6W'fF�����7B�f��Ɨ�F���VF�B&��6���r�6���6W"&W�6V�V�B��BWF��L�]�[�\��X���[�
�[��
HO�[�[�HY][�B�����X��[��H�]�[�\��X���[��\�\��\�[]\�[���\�ˈ���]HH�YX�Qܚ[
�]K�\N�	��T��QU��P���S�	�[�^�JB�\��\��\]X[
�]K�Y][��[�^
B�\��\��\]X[
�]K�Y\��[���B�\��\��\]X[
�]K�Y\��WK�[���\�	�\���[�[ؚ[I�	�]\�[���\�H�\�\��Y	�B�\��\��\]X[
�]K�Y\�̗K�[���\�	��S]I�	�]\�[���\���\�\��Y	�B������[�[�HY]�]]�\�]�H�]�]H�]�H�]ۈ[��]\���HY\������'�]\���HY\��'HYX[��^][�[�HY][��[[YYX][HY�\�H�[��H\���[Z]Y����]HH�YX�Qܚ[
�]K�\N�	��U�W��P���S�	�[�^�[���\��	�]�[���\��[���JB�\��\��\]X[
�]K�Y][��[�^�[	ԙ]\��Y�HY\��B�\��\��\]X[
�]K�Y\��K�[���\�	�]�[���\��[���	�\]Y[���\���[Z]Y	�B�\��\��\]X[
�]K�Y\��WK�[���\�	�\���[�[ؚ[I�	�]\�[���\�H�\�\��YY�\��]�I�B�\��\��\]X[
�]K�Y\�̗K�[���\�	��S]I�	�]\�[���\���\�\��YY�\��]�I�B����ˈ�[[ݙH�X���[�B�����[[ݚ[��H�X���[��\�\��\�]\�[���\��[�X]�\�H�[XZ[�[��Y\�\�X�K����]HH�YX�Qܚ[
�]K�\N�	ԑSSՑW��P���S�	�[�^�HJB�\��\��\]X[
�]K�Y\��[���B�\��\��\]X[
�]K�Y\��K�[���\�	�]�[���\��[���B�\��\��\]X[
�]K�Y\��WK�[���\�	��S]I�	�]\�[���\��\�\��YY�\��[[ݘ[وX\�Y\��[���B�\��\��\]X[
�]K�Y][��[�^�[
B�����\�Y�H�[XZ[�[��Y\�\��[\�X�H�܈Y][��]HH�YX�Qܚ[
�]K�\N�	��T��QU��P���S�	�[�^�HJB�\��\��\]X[
�]K�Y][��[�^JB��]HH�YX�Qܚ[
�]K�\N�	��U�W��P���S�	�[�^�K[���\��	�[�^Y��JB�\��\��\]X[
�]K�Y\��WK�[���\�	�[�^Y��B�\��\��\]X[
�]K�Y][��[�^�[
B������[�[^�][ۈ	���Y�[�[^�][ۈY]����[���[�\��\��YO��[�[^�][ۈ�Y�[��]HH�YX�Qܚ[
�]K�\N�	�ԒUWД�QQ��JB�\��\��\]X[
�]K��]\�	؜�YY�[���B�����[H��YY�[��Y]�]\��H����Y�\��\��Y\\]X[
�YX�Qܚ[
�]K�\N�	��T��QU��P���S�	�[�^�JK�]JB�\��\��Y\\]X[
�YX�Qܚ[
�]K�\N�	��U�W��P���S�	�[�^�[���\��	ӛ�[�	�JK�]JB�\��\��Y\\]X[
�YX�Qܚ[
�]K�\N�	ԑSSՑW��P���S�	�[�^�JK�]JB������YY�\��XYB��ۜ��[�[^�Y��\H�[�X�М�YY��]K�[�[��]K�Y\�B��]HH�YX�Qܚ[
�]K�\N�	Д�QQ�ԑPQI���YY���[�[^�Y��\JB�\��\��\]X[
�]K��]\�	ٚ[�[^�Y	�B�\��\��\]X[
�]K��[�[^�Y�YJB����Y�\��[�[^�][ۋY]�]\��H����Y�����X���[��\�HY]X�HۛH�Y�ܙH�[�[^�][ۋ������\�X�H�X���[�Y][��Y�\��[�[^�][ۋ���\��\��Y\\]X[
�YX�Qܚ[
�]K�\N�	��T��QU��P���S�	�[�^�JK�]JB�\��\��Y\\]X[
�YX�Qܚ[
�]K�\N�	��U�W��P���S�	�[�^�[���\��	ӛ�[�	�JK�]JB�\��\��Y\\]X[
�YX�Qܚ[
�]K�\N�	ԑSSՑW��P���S�	�[�^�JK�]JB����K���\��\��\X�[Y[�[�]]�X]X����B����Y�\�[���\�[��ܚ[]Y\�[ۜ�[��\��[��[�\�H�[�[^�Y��\�\X�\�H��\��\��۝[��\�X�K������ܚ[���\�]]�X]X�[HY�\�X�[��H��\[�H��\��\�����Z�P��\��\��ܚ]Q�Y�
�]K���YY�B��]HH�YX�Qܚ[
�]K�\N�	ԑT�U	�JB��\��\��\]X[
�]K��]\�	�YI�	�ܚ[���Y]]�X]X�[I�B�\��\�����Z�P��\��\���XY�Y�

K�[��Y\�	�����[��Z[[�ٙ�[�H�[����	�K	���\�\X�Y��\��\��۝[��\�X�I�B�\��\�����Z�P��\��\���XY�Y�

K�[��Y\�	�]�[���\��[���K	�Y]Y�X���[��Y�X�Y[��[�[^�Y��\	�B�\��\�����Z�P��\��\���XY�Y�

K�[��Y\�	�[�^Y��K	��\�\��Y]\��X���[��Y�X�Y[��[�[^�Y��\	�B�\��\����Y�Z�P��\��\���XY�Y�

K�[��Y\�	�\���[�[ؚ[I�K	ԙ[[ݙY�X���[�^�YY���H�[�[^�Y��\	�B�JB��\�
	��X���[�Y]X�[ۜ��\]Z\�HH�[Y�[��[�Y]X�H�]\��

HO��ۜ��]HH���[�]X[ܚ[�]J
K�Y\����[���\��	��Y\	��]Y�ܞN�	���[	�]Y\�[ێ�	�I��X��[Y[�Y�	ԉ��]Y���T�X��[Y[�][ێ��[�HWK��]\Έ	�X�]�IB�\��\��Y\\]X[
�YX�Qܚ[
�]K�\N�	��T��QU��P���S�	�[�^�LHJK�]JB�\��\��Y\\]X[
����^N��[�K�^N�	�X��Y]R�^N��[�K�Y��^N��[�K\��]K����[���]\Έ	�X�]�I�JK�[�JB�JB��\�
	٘[�X����YY��\��Y\��\\�Y[�[�[��]Y\�X�]�\��]�][��[�Y�X���

HO��ۜ���YY�H�[�X�М�YY�	�[\[Y[�H\���[���[���\��	���Z[�Y�[���]Y�ܞN�	�[]�\�X�I�]Y\�[ێ�	��]��[[����X��[Y[�Y�	���Z[�Y�[���]Y���T�X��[Y[�][ێ��[�HB�JB�\��\��\]X[
���YY��	�����[�[\[Y[�H\���[������]YX�\�[ۜ��H[]�\�X�H8�%�]��[[�Έ��Z[�Y�[�����\��[\[ۜ��XZ�H^X�]H
���\��W�H�ۙH�\\�Y[�HY\������\�X�]�W��ܚ�]]ۛ�[�\�K�����KX\��[�][��X�ݙK�\��ۛHY�����Y�H��Y][���]�YH\���YY��
B�JB��\�
	�[�]X[��\��\�]X�Y[���\��]�HHܚ[[��Y�X�X�H[��[����[��H\�]Y\�[ۉ�

HO��ۜ��ܙY[���H�Y�	��ܙY[�LI��[��	�[XY�I��[YN�	��ܙY[�����]W�\��	�]N�[XY�K���ؘ\�M�POOI��^�N��B��ۜ���\�H�Y�	ۛ�\�LI��[��	ٚ[I��[YN�	ۛ�\˝	��۝[��	��Y\H�\��[��]�Y�][ۋ���^�N��B�]�]HH�YX�Qܚ[
[�]X[ܚ[�]J
K�\N�	��T�	�]X�Y[�Έ��ܙY[���K[�[��	ԙY�[�HH\���Y�[��JB�\��\��Y\\]X[
�]K�]X�Y[����ܙY[���JB���]HH�YX�Qܚ[
�]K�\N�	�UP��QQPI�]X�Y[�Έۛ�\�HJB�\��\��Y\\]X[
�]K�]X�Y[����ܙY[���K	�\�\]Y\�[ۈ]X�Y[�X�[ۜ�]\����[��H[�]X[��\��\��۝^	�B��]HH�YX�Qܚ[
�]K�\N�	ԑSSՑW�UP�QS�	�Y��ܙY[����YJB�\��\��Y\\]X[
�]K�]X�Y[����ܙY[���K	�\�\]Y\�[ۈ�[[ݘ[]\����[��H[�]X[��\��\��۝^	�B���]HH�YX�Qܚ[
�]K�\N�	�S�T����USӉ��\�ۜ�N��ۙN��YHHJB��]HH�YX�Qܚ[
�]K�\N�	�ԒUWД�QQ��JB�\��\��\]X[
�]K��]\�	؜�YY�[���B�\��\��Y\\]X[
�]K�]X�Y[����ܙY[���K	؜�YY��\]Y\���]Z[�H[�]X[��\��\�]X�Y[�^[�Y	�B�JB��\�
	�Y�[�^��\���\�\]Y\�[ۈYYXH]X�Y[��۝����\�[��

HO��ۜ�Y�[�H]�Z]�XY�[J�]�T�
	ˋ�ˋ��\����Y�[�����[\ܝ�Y]K�\�
K	�]�	�B�\��\���\ӛ�X]�
Y�[�ٝ[��[ۈ]X�Y[��۝����B�\��\���\ӛ�X]�
Y�[��]KYܚ[X]X�[YYXK�B�\��\���\ӛ�X]�
Y�[��]KYܚ[X]X�Y[�Z[�]�B�\��\���\ӛ�X]�
Y�[��ۑ�Y�ݙ\���B�\��\���\ӛ�X]�
Y�[��ۑ����B�\��\���\ӛ�X]�
Y�[��۔\�N��B�\��\���\ӛ�X]�
Y�[���\�X[^�P]X�Y[���B�JB��\�
	؜�YY�X�[Y[��ܝ�\��H[��[��Y]X�Y[�^[�Y�H��\��\�Y\\��\�[��

HO��ۜ�Y�[�H]�Z]�XY�[J�]�T�
	ˋ�ˋ��\����Y�[�����[\ܝ�Y]K�\�
K	�]�	�B�\��\��X]�
Y�[��]X�Y[�Έ�\]Y\��]W�]X�Y[���B�\��\��X]�
Y�[����\��\�Y\\���ܝ�\�]X�Y[��
�\]Y\��]W�]X�Y[��
K�B�\��\��X]�
Y�[�ٛܝ�\�]X�Y[��
]X�Y[��
H��B�JB��\�
	��T�[��U��T��Sӗ�T�ԖH�\�\��H[��X�Y�[܈�۝�\��][ۈ�۝^	�

HO��ۜ�\�ܞHH���N�	�\�\���۝[��	�H^\�[�����\�[�[�[ۘ[H�^X��\�Y�\����K����N�	�\��\�[�	��۝[��	�H�[�Y\HXZ[���\��\��Z]�[܈[�X���B�B�]�]HH�YX�Qܚ[
[�]X[ܚ[�]J
K�\N�	��T�	�[�[��	�YYYXH�\ܝ	��\��[ے\�ܞN�\�ܞHJB�\��\��Y\\]X[
�]K��\��[ے\�ܞK\�ܞJB���ۜ��\X�[Y[�H����N�	�\�\���۝[��	�[��[��YHH]X�Y�ܙY[�����WB��]HH�YX�Qܚ[
�]K�\N�	��U��T��Sӗ�T�ԖI��\��[ے\�ܞN��\X�[Y[�JB�\��\��Y\\]X[
�]K��\��[ے\�ܞK�\X�[Y[�
B�\��\��Y\\]X[
�YX�Qܚ[
�]K�\N�	��U��T��Sӗ�T�ԖI��\��[ے\�ܞN��[JK��\��[ے\�ܞK�JB�JB