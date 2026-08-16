const app = getApp()
Page({
  data: { input: "", messages: [], conversationId: "", loading: false },
  onInput(e) { this.setData({ input: e.detail.value }) },
  send() {
    const text = this.data.input.trim()
    if (!text || this.data.loading) return
    this.setData({ input: "", loading: true, messages: [...this.data.messages, { role: "user", content: text, sources: [] }] })
    wx.request({ url: `${app.globalData.apiBase}/api/chat`, method: "POST", data: { message: text, conversation_id: this.data.conversationId || null },
      success: ({data}) => this.setData({ conversationId: data.conversation_id, messages: [...this.data.messages, { role: "assistant", content: data.answer, sources: data.sources || [] }] }),
      fail: () => wx.showToast({ title: "无法连接后端", icon: "none" }), complete: () => this.setData({ loading: false }) })
  }
})

