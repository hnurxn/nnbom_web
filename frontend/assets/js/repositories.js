// repositories.html Vue.js 应用
const { createApp } = Vue;

createApp({
  data() {
    return {
      items: [],
      total: 0,
      page: 1,
      perPage: 24,
      sortBy: 'stars',
      order: 'desc',
      q: '',
      isLoading: false
    }
  },
  computed: {
    totalPages() {
      return Math.max(1, Math.ceil(this.total / this.perPage));
    }
  },
  methods: {
    async load(page = 1) {
      this.page = page;
      this.isLoading = true;
      try {
        const params = new URLSearchParams({ 
          page: this.page, 
          per_page: this.perPage, 
          sort_by: this.sortBy, 
          order: this.order 
        });
        if (this.q && this.q.trim()) params.append('q', this.q.trim());
        
        const res = await fetch(`http://localhost:5001/api/repos?${params.toString()}`);
        if (!res.ok) throw new Error('Network error ' + res.status);
        const data = await res.json();
        if (!data.success) throw new Error(data.message || 'Backend error');
        
        this.items = data.items;
        this.total = data.total;
      } catch (err) {
        console.error(err);
        alert('Failed to load repositories: ' + err.message);
      } finally {
        this.isLoading = false;
      }
    },
    goToRepo(repo) {
      if (!repo) return;
      try {
        localStorage.setItem('selectedRepo', JSON.stringify(repo));
      } catch (err) {
        console.warn('无法缓存仓库详情', err);
      }
      window.location.href = `repository.html?id=${encodeURIComponent(repo.id)}`;
    }
  },
  mounted() {
    this.load(1);
  }
}).mount('#app');
