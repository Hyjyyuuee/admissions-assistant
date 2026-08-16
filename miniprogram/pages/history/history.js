const app = getApp()
Page({ data: { items: [] }, onShow() { wx.request({ url: `${app.globalData.apiBase}/api/conversations`, success: ({data}) => this.setData({ items: data }) }) } })

