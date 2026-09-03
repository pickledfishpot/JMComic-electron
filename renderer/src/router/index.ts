import { createRouter, createWebHashHistory } from "vue-router";
import HomeView from "../views/HomeView.vue";
import BookDetailView from "../views/BookDetailView.vue";
import SearchView from "../views/SearchView.vue";
import CategoriesView from "../views/CategoriesView.vue";

const routes = [
  { path: "/", name: "home", component: HomeView },
  {
    path: "/book/:id",
    name: "book-detail",
    component: BookDetailView,
    props: true,
  },
  { path: "/search", name: "search", component: SearchView },
  { path: "/categories", name: "categories", component: CategoriesView },
];

export const router = createRouter({
  history: createWebHashHistory(),
  routes,
});
