import { createRouter, createWebHashHistory } from "vue-router";
import HomeView from "../views/HomeView.vue";
import BookDetailView from "../views/BookDetailView.vue";
import SearchView from "../views/SearchView.vue";
import CategoriesView from "../views/CategoriesView.vue";
import ReadView from "../views/ReadView.vue";
import LoginView from "../views/LoginView.vue";
import FavoritesView from "../views/FavoritesView.vue";
import HistoryView from "../views/HistoryView.vue";
import DownloadsView from "../views/DownloadsView.vue";
import LocalLibraryView from "../views/LocalLibraryView.vue";
import NasView from "../views/NasView.vue";
import SettingsView from "../views/SettingsView.vue";
import ToolsView from "../views/ToolsView.vue";

const routes = [
  { path: "/", name: "home", component: HomeView },
  {
    path: "/book/:id",
    name: "book-detail",
    component: BookDetailView,
    props: true,
  },
  {
    path: "/read/:bookId/:epsIndex?",
    name: "read",
    component: ReadView,
    props: true,
  },
  {
    path: "/local/read/:bookId/:epsIndex?",
    name: "local-read",
    component: ReadView,
    props: (route) => ({
      bookId: route.params.bookId,
      epsIndex: route.params.epsIndex,
      local: "1",
    }),
  },
  { path: "/local", name: "local", component: LocalLibraryView },
  { path: "/nas", name: "nas", component: NasView },
  { path: "/settings", name: "settings", component: SettingsView },
  { path: "/tools", name: "tools", component: ToolsView },
  { path: "/search", name: "search", component: SearchView },
  { path: "/categories", name: "categories", component: CategoriesView },
  { path: "/login", name: "login", component: LoginView },
  { path: "/favorites", name: "favorites", component: FavoritesView },
  { path: "/history", name: "history", component: HistoryView },
  { path: "/downloads", name: "downloads", component: DownloadsView },
];

export const router = createRouter({
  history: createWebHashHistory(),
  routes,
});
