import { api } from "../api.js";
import useLoad from "./useLoad.js";

export default function useHousehold() {
  const { data } = useLoad(() => api("/households/"));
  return data?.results?.[0];
}