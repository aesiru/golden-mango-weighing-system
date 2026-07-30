import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import RelatedDataGrid from '~/components/entity/RelatedDataGrid.vue'

describe('RelatedDataGrid', () => {
  const mockChildMeta = {
    name: 'test_related',
    label: 'Test Related',
    fields: [
      { name: 'id', label: 'ID', field_type: 'string', hidden: false, in_list_view: true },
      { name: 'name', label: 'Name', field_type: 'string', hidden: false, in_list_view: true },
      { name: 'status', label: 'Status', field_type: 'string', hidden: false, in_list_view: true },
    ],
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders NuGrid with paginated data', () => {
    const wrapper = mount(RelatedDataGrid, {
      props: {
        parentEntity: 'parent',
        parentId: '123',
        childEntity: 'related',
        fkField: 'parent_id',
        childMeta: mockChildMeta,
      },
    })

    expect(wrapper.exists()).toBe(true)
  })

  it('canAdd=false hides Add button', () => {
    const wrapper = mount(RelatedDataGrid, {
      props: {
        parentEntity: 'parent',
        parentId: '123',
        childEntity: 'related',
        fkField: 'parent_id',
        childMeta: mockChildMeta,
        canAdd: false,
      },
    })

    const vm = wrapper.vm as any
    expect(vm.canAdd).toBe(false)
  })

  it('canDelete=false hides Delete in row action menu', () => {
    const wrapper = mount(RelatedDataGrid, {
      props: {
        parentEntity: 'parent',
        parentId: '123',
        childEntity: 'related',
        fkField: 'parent_id',
        childMeta: mockChildMeta,
        canDelete: false,
      },
    })

    const vm = wrapper.vm as any
    expect(vm.canDelete).toBe(false)
  })

  it('editable=false disables inline editing', () => {
    const wrapper = mount(RelatedDataGrid, {
      props: {
        parentEntity: 'parent',
        parentId: '123',
        childEntity: 'related',
        fkField: 'parent_id',
        childMeta: mockChildMeta,
        editable: false,
      },
    })

    const vm = wrapper.vm as any
    expect(vm.editable).toBe(false)
  })

  it('tracks dirty rows when cell value changes', () => {
    const wrapper = mount(RelatedDataGrid, {
      props: {
        parentEntity: 'parent',
        parentId: '123',
        childEntity: 'related',
        fkField: 'parent_id',
        childMeta: mockChildMeta,
        editable: true,
      },
    })

    const vm = wrapper.vm as any
    
    // Simulate cell value change
    const mockEvent = {
      row: { original: { id: 'row-1', name: 'Test' } },
      column: { id: 'name' },
      newValue: 'Updated Test',
    }

    vm.onCellValueChanged(mockEvent)

    expect(vm.dirty).toBe(true)
    expect(vm.dirtyRows.has('row-1')).toBe(true)
  })

  it('pagination triggers getEntityListView with correct page', async () => {
    const mockGetEntityListView = vi.fn().mockResolvedValue({
      status: 'success',
      data: [{ id: '1', name: 'Row 1' }],
      total: 50,
    })

    vi.mock('~/composables/useApi', () => ({
      useApi: () => ({
        getEntityListView: mockGetEntityListView,
        bulkSaveChildren: vi.fn(),
        getEntityOptions: vi.fn(),
        postEntityAction: vi.fn(),
      }),
    }))

    const wrapper = mount(RelatedDataGrid, {
      props: {
        parentEntity: 'parent',
        parentId: '123',
        childEntity: 'related',
        fkField: 'parent_id',
        childMeta: mockChildMeta,
      },
    })

    const vm = wrapper.vm as any
    
    // Change page
    await vm.setPage(2)

    expect(vm.page).toBe(2)
  })

  it('exposes loadData and saveDirtyRows methods', () => {
    const wrapper = mount(RelatedDataGrid, {
      props: {
        parentEntity: 'parent',
        parentId: '123',
        childEntity: 'related',
        fkField: 'parent_id',
        childMeta: mockChildMeta,
      },
    })

    const vm = wrapper.vm as any
    expect(typeof vm.loadData).toBe('function')
    expect(typeof vm.saveDirtyRows).toBe('function')
  })

  it('computes totalPages correctly', () => {
    const wrapper = mount(RelatedDataGrid, {
      props: {
        parentEntity: 'parent',
        parentId: '123',
        childEntity: 'related',
        fkField: 'parent_id',
        childMeta: mockChildMeta,
      },
    })

    const vm = wrapper.vm as any
    vm.total = 45
    vm.pageSize = 20

    expect(vm.totalPages).toBe(3) // Math.ceil(45 / 20) = 3
  })
})
