<script setup lang="ts">
import { h, resolveComponent } from "vue";
import type { TableColumn } from "@nuxt/ui";
import AdminFormModal from "~/components/admin/AdminFormModal.vue";
import { useDeleteModalStore } from "~/stores/deleteModal";

const UButton = resolveComponent("UButton");
const UBadge = resolveComponent("UBadge");
const UAvatar = resolveComponent("UAvatar");
const UIcon = resolveComponent("UIcon");
const USlideover = resolveComponent("USlideover");

const api = useApi();
const toast = useToast();

const deleteModalStore = useDeleteModalStore();

// Data
const users = ref<any[]>([]);
const roles = ref<any[]>([]);
const loading = ref(true);
const error = ref("");
const userMetadata = ref<any>(null);

const pagination = ref({
  page: 1,
  pageSize: 10,
  total: 0,
});

// Modal state
const showUserModal = ref(false);
const editingUser = ref<any>(null);
const isModalLoading = ref(false);
const userModalRef = ref<any>(null);

watch([() => pagination.value.page, () => pagination.value.pageSize], () => {
  loadUsers();
});

// Columns definition
const userColumns: TableColumn<any>[] = [
  {
    accessorKey: "full_name",
    header: "User",
    cell: ({ row }) =>
      h("div", { class: "flex items-center gap-3" }, [
        h(UAvatar, { size: "sm", alt: row.original.full_name }),
        h("div", { class: "truncate" }, [
          h("div", { class: "font-medium" }, row.original.full_name),
          h(
            "div",
            { class: "text-muted-foreground text-sm" },
            row.original.username,
          ),
        ]),
      ]),
  },
  {
    accessorKey: "email",
    header: "Email",
  },
  {
    accessorKey: "roles",
    header: "Roles",
    cell: ({ row }) =>
      h(
        "div",
        { class: "flex flex-wrap gap-1" },
        row.original.roles.map((role: any) =>
          h(UBadge, { variant: "soft", size: "md" }, () => role.name),
        ),
      ),
  },
  {
    accessorKey: "is_active",
    header: "Status",
    cell: ({ row }) =>
      h(
        UBadge,
        {
          color: row.original.is_active ? "success" : "error",
          variant: "subtle",
          size: "md",
        },
        () => (row.original.is_active ? "Active" : "Inactive"),
      ),
  },
  {
    id: "actions",
    header: "",
    cell: ({ row }) =>
      h("div", { class: "flex items-center gap-2" }, [
        h(UButton, {
          variant: "ghost",
          size: "xs",
          icon: "i-lucide-edit",
          onClick: () => openEditModal(row.original),
        }),
        h(UButton, {
          variant: "ghost",
          size: "xs",
          icon: "i-lucide-trash-2",
          color: "error",
          onClick: () => openDeleteModal(row.original),
        }),
      ]),
  },
];

// Methods
const loadUsers = async () => {
  try {
    loading.value = true;
    const [usersRes, rolesRes, metaRes] = await Promise.all([
      api.getAdminUsers(
        (pagination.value.page - 1) * pagination.value.pageSize,
        pagination.value.pageSize,
      ),
      api.getAdminRoles(),
      api.getAdminUserMeta(),
    ]);
    users.value = usersRes.data?.users || [];
    pagination.value.total = usersRes.data?.total || 0;
    roles.value = rolesRes.data || [];
    userMetadata.value = metaRes.data;
  } catch (err: any) {
    error.value = err.message || "Failed to load data";
    toast.add({ title: "Failed to load data", color: "error" });
  } finally {
    loading.value = false;
  }
};

const openCreateModal = () => {
  console.log("[AdminUsers] create clicked");
  editingUser.value = null;
  showUserModal.value = true;
  console.log("[AdminUsers] showUserModal ->", showUserModal.value);
};

const openEditModal = (user: any) => {
  console.log("[AdminUsers] edit clicked", user);
  editingUser.value = user;
  showUserModal.value = true;
  console.log("[AdminUsers] showUserModal ->", showUserModal.value);
};

const openDeleteModal = (user: any) => {
  deleteModalStore.open({
    entityName: "User",
    itemName: user.full_name || user.email,
    itemId: user.id,
    onConfirm: async () => {
      const response = await api.deleteUser(user.id);
      if (response.status === "success") {
        toast.add({ title: response.message, color: "success" });
        await loadUsers();
      } else {
        throw new Error(response.message || "Delete failed");
      }
    },
  });
};

const saveUser = async (userData: any) => {
  try {
    isModalLoading.value = true;

    if (editingUser.value) {
      const response = await api.updateUser(editingUser.value.id, userData);
      if (response.status === "success") {
        toast.add({ title: response.message, color: "success" });
        showUserModal.value = false;
        await loadUsers();
      } else {
        // Check if there are field-specific errors
        if (response.data?.errors) {
          // Pass the error response back to the modal
          userModalRef.value?.handleError(response);
          return;
        } else {
          toast.add({ title: response.message, color: "error" });
        }
      }
    } else {
      const response = await api.createUser(userData);
      if (response.status === "success") {
        toast.add({ title: response.message, color: "success" });
        showUserModal.value = false;
        await loadUsers();
      } else {
        // Check if there are field-specific errors
        if (response.data?.errors) {
          // Pass the error response back to the modal
          userModalRef.value?.handleError(response);
          return;
        } else {
          toast.add({ title: response.message, color: "error" });
        }
      }
    }
  } catch (err: any) {
    // If the error has field-specific errors, pass it to the modal
    if (err.data?.errors) {
      userModalRef.value?.handleError(err);
    } else {
      toast.add({
        title: err.message || "Failed to save user",
        color: "error",
      });
    }
  } finally {
    isModalLoading.value = false;
  }
};

const handleFormError = (error: any) => {
  console.error("Form error:", error);
};

const assignRole = async (userId: string, roleId: string) => {
  try {
    const response = await api.assignRoleToUser(userId, roleId);
    if (response.status === "success") {
      toast.add({ title: response.message, color: "success" });
      await loadUsers();
    } else {
      toast.add({ title: response.message, color: "error" });
    }
  } catch (err: any) {
    toast.add({ title: "Failed to assign role", color: "error" });
  }
};

const removeRole = async (userId: string, roleId: string) => {
  try {
    const response = await api.removeRoleFromUser(userId, roleId);
    if (response.status === "success") {
      toast.add({ title: response.message, color: "success" });
      await loadUsers();
    } else {
      toast.add({ title: response.message, color: "error" });
    }
  } catch (err: any) {
    toast.add({ title: "Failed to remove role", color: "error" });
  }
};

// Load data on mount
onMounted(() => {
  loadUsers();
});

definePageMeta({ title: "Users" });
</script>

<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <h2 class="text-xl font-semibold">Users</h2>
      <UButton @click="openCreateModal" icon="i-lucide-plus">
        Add User
      </UButton>
    </div>

    <div class="border border-accented rounded-lg space-y-4">
      <!-- Loading state -->
      <div v-if="loading" class="flex items-center justify-center py-12">
        <UIcon
          name="i-lucide-loader-2"
          class="animate-spin h-8 w-8 text-primary"
        />
      </div>

      <!-- Users Table -->
      <div v-else-if="users.length > 0">
        <div class="overflow-x-auto">
          <UTable :data="users" :columns="userColumns" />
        </div>

        <!-- Pagination -->
        <div class="flex justify-end pt-4 border-t border-accented px-4 py-3.5">
          <UPagination
            :page="pagination.page"
            :items-per-page="pagination.pageSize"
            :total="pagination.total"
            @update:page="(p) => (pagination.page = p)"
          />
        </div>
      </div>

      <!-- Empty state -->
      <div
        v-else
        class="text-center py-24 border border-dashed border-accented rounded-lg bg-muted/10"
      >
        <UIcon
          name="i-lucide-users"
          class="h-12 w-12 text-muted-foreground mx-auto mb-4"
        />
        <p class="text-muted-foreground font-medium text-sm">No users found</p>
      </div>
    </div>

    <!-- User Create/Edit Modal -->
    <AdminFormModal
      ref="userModalRef"
      v-model="showUserModal"
      entity-type="users"
      :editing-item="editingUser"
      :metadata="userMetadata"
      :roles="roles"
      :loading="isModalLoading"
      @save="saveUser"
      @error="handleFormError"
    />
  </div>
</template>
