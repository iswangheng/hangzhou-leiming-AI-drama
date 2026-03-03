// ============================================
// DramaCut AI 数据库层统一导出
// ============================================

// 导出数据库客户端
export { db, dbClient } from './client';

// 导出 Schema 类型
export * from './schema';

// 导出 Schema 对象（包含所有表）
export { schema } from './schema';

// 导出查询工具
export * from './queries';
