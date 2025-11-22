// index.html Vue.js 应用
const { createApp } = Vue;

createApp({
  data() {
    return {
      total: 0
    }
  },
  methods: {
    async loadStats() {
      try {
        const res = await fetch(`http://localhost:5001/api/repos?page=1&per_page=1`);
        if (!res.ok) throw new Error('网络错误 ' + res.status);
        const data = await res.json();
        if (!data.success) throw new Error(data.message || '后端错误');
        this.total = data.total;
      } catch (err) {
        console.error(err);
      }
    }
  },
  mounted() {
    this.loadStats();
  }
}).mount('#app');
