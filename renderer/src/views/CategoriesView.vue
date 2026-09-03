<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { assetUrl } from "../api/client";
import {
  getCategories,
  getCategoryBooks,
  type BookItem,
  type Category,
  type CategoryBooksResponse,
} from "../api/books";
import PageHeader from "../components/PageHeader.vue";
import BookCard from "../components/BookCard.vue";
import PillTabs from "../components/PillTabs.vue";
import StateBlock from "../components/StateBlock.vue";

const router = useRouter();

const loading = ref(false);
const error = ref<string | null>(null);
const categories = ref<Category[]>([]);
const activeSlug = ref<string>("0");
const booksResult = ref<CategoryBooksResponse | null>(null);
// 书籍列表请求序号：快速切换分类/排序时，仅采纳最新一次响应
let booksReqSeq = 0;

const sortOptions = [
  { value: "mr", label: "最新" },
  { value: "mv", label: "最多点击" },
  { value: "mv_m", label: "月排行" },
  { value: "mv_w", label: "周排行" },
  { value: "mv_t", label: "日排行" },
  { value: "mp", label: "最多图片" },
  { value: "tf", label: "最多爱心" },
];

async function loadCategories() {
  loading.value = true;
  error.value = null;
  try {
    const res = await getCategories();
    categories.value = res.categories;
  } catch (err) {
    error.value = String(err);
  } finally {
    loading.value = false;
  }
}

async function loadCategoryBooks(slug: string, page = 1, sort = "mr") {
  const seq = ++booksReqSeq;
  loading.value = true;
  error.value = null;
  try {
    const res = await getCategoryBooks(slug, page, sort);
    if (seq !== booksReqSeq) return; // 过期响应
    booksResult.value = res;
    activeSlug.value = slug;
  } catch (err) {
    if (seq === booksReqSeq) error.value = String(err);
  } finally {
    if (seq === booksReqSeq) loading.value = false;
  }
}

/** 分类列表失败重试：恢复后若书籍从未加载成功，补一次加载 */
async function retryCategories() {
  await loadCategories();
  if (!booksResult.value) {
    loadCategoryBooks(activeSlug.value);
  }
}

function openBook(book: BookItem) {
  router.push({ name: "book-detail", params: { id: book.id } });
}

onMounted(() => {
  // 分类列表失败不阻塞书籍加载（默认「全部」不依赖分类数据）
  loadCategories().finally(() => loadCategoryBooks("0"));
});
</script>

<template>
  <div class="min-h-screen bg-canvas text-ink">
    <PageHeader title="分类" />

    <main class="p-6">
      <StateBlock v-if="loading && !categories.length" type="loading" />
      <StateBlock
        v-else-if="error"
        type="error"
        :message="error"
        @retry="retryCategories"
      >
        <p class="mt-2 text-sm text-muted-soft">
          JM 服务器不太稳定，若重试三次仍失败，可能是对方服务器问题。
        </p>
      </StateBlock>

      <div v-else class="space-y-6">
        <PillTabs
          :model-value="activeSlug"
          :options="[
            { value: '0', label: '全部' },
            ...categories.map((c) => ({ value: c.slug, label: c.name })),
          ]"
          @update:model-value="(v) => loadCategoryBooks(v)"
        />

        <div class="flex flex-wrap items-center justify-between gap-3">
          <p class="text-sm text-muted">
            {{ booksResult ? `共 ${booksResult.total} 本` : "" }}
          </p>
          <PillTabs
            :model-value="booksResult?.sort || 'mr'"
            :options="sortOptions"
            size="sm"
            @update:model-value="(v) => loadCategoryBooks(activeSlug, 1, v)"
          />
        </div>

        <div
          v-if="booksResult"
          class="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6"
        >
          <BookCard
            v-for="book in booksResult.books"
            :key="book.id"
            :cover="assetUrl(book.coverUrl)"
            :title="book.title"
            :author="book.authorList.join(', ') || '未知作者'"
            @open="openBook(book)"
          />
        </div>
      </div>
    </main>
  </div>
</template>
