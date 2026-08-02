'use client'

import { Suspense, useEffect, useRef, useState, useCallback, useMemo } from 'react'
import { Canvas, useThree } from '@react-three/fiber'
import { OrbitControls, GizmoHelper, GizmoViewport, Bounds, useBounds } from '@react-three/drei'
import * as THREE from 'three'
import { STLLoader } from 'three/examples/jsm/loaders/STLLoader.js'
import { Box, RotateCcw, ArrowUp, ArrowRight, CircleDot, Triangle } from 'lucide-react'
import { layOutCutField, type PartSize } from '@/lib/bedLayout'
import { FACTORY_BIN_CONFIG } from '@/lib/binDefaults'

interface Props {
  stlUrl: string
  splitUrls?: string[]
  insertUrl?: string
  /** print bed edge length in mm; the floor grid is drawn at this size */
  bedSize?: number
  /** the field the backend cut splitUrls into; 0 when there is no regular one */
  splitCols?: number
  splitRows?: number
}

// only used when a caller renders the preview without a configured bed size
const DEFAULT_BED_SIZE = FACTORY_BIN_CONFIG.bed_size
// target cell size; the real cell is the bed divided into whole cells. Not the
// 42mm gridfinity unit -- this grid measures the print bed, not the bin.
const GRID_CELL_MM = 10

type CameraView = 'home' | 'top' | 'front' | 'right' | 'fit'

type RenderMode = 'solid' | 'edges'

function StlModel({ url, renderMode, color = '#5ab4de', edgeColor = '#1e3d5c' }: { url: string; renderMode: RenderMode; color?: string; edgeColor?: string }) {
  const [geometry, setGeometry] = useState<THREE.BufferGeometry | null>(null)
  const [edgesGeometry, setEdgesGeometry] = useState<THREE.EdgesGeometry | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)

  useEffect(() => {
    const loader = new STLLoader()
    let disposed = false
    let loadedGeo: THREE.BufferGeometry | null = null
    let loadedEdges: THREE.EdgesGeometry | null = null

    loader.load(
      url,
      (geo) => {
        if (disposed) { geo.dispose(); return }
        geo.computeVertexNormals()

        geo.computeBoundingBox()
        const box = geo.boundingBox!
        const centerX = (box.max.x + box.min.x) / 2
        const centerY = (box.max.y + box.min.y) / 2
        const minZ = box.min.z

        geo.translate(-centerX, -centerY, -minZ)
        loadedGeo = geo
        loadedEdges = new THREE.EdgesGeometry(geo, 30)
        setGeometry(geo)
        setEdgesGeometry(loadedEdges)
      },
      () => {},
      (err) => {
        console.error('STL load error:', err)
        setLoadError(String(err))
      }
    )

    return () => {
      disposed = true
      loadedGeo?.dispose()
      loadedEdges?.dispose()
    }
  }, [url])

  if (loadError || !geometry) return null

  return (
    <group rotation={[-Math.PI / 2, 0, 0]}>
      {renderMode === 'solid' ? (
        <>
          <mesh geometry={geometry}>
            <meshStandardMaterial color={color} metalness={0} roughness={0.7} />
          </mesh>
          {edgesGeometry && (
            <lineSegments geometry={edgesGeometry}>
              <lineBasicMaterial color={edgeColor} linewidth={1} />
            </lineSegments>
          )}
        </>
      ) : (
        <>
          <mesh geometry={geometry}>
            <meshStandardMaterial color="#27272a" metalness={0} roughness={1} transparent opacity={0.3} />
          </mesh>
          {edgesGeometry && (
            <lineSegments geometry={edgesGeometry}>
              <lineBasicMaterial color={color} linewidth={1} />
            </lineSegments>
          )}
        </>
      )}
    </group>
  )
}

const SPLIT_PIECE_COLORS = ['#4a9eff', '#ff6b4a', '#4aff9e', '#ff4adb']
const SPLIT_PIECE_GAP_MM = 10

interface LoadedPiece {
  geo: THREE.BufferGeometry
  edges: THREE.EdgesGeometry
  size: PartSize
}

function SplitModels(
  { urls, renderMode, cols, rows }:
  { urls: string[]; renderMode: RenderMode; cols: number; rows: number }
) {
  const [pieces, setPieces] = useState<LoadedPiece[]>([])

  // keyed on urls alone: the layout must not re-download every piece when the
  // bed size or the cut plan changes
  useEffect(() => {
    const loader = new STLLoader()
    let cancelled = false
    let loadedPieces: LoadedPiece[] = []

    Promise.all(urls.map(url =>
      new Promise<THREE.BufferGeometry | null>((resolve) => {
        loader.load(url, (geo) => { geo.computeVertexNormals(); resolve(geo) }, () => {}, () => resolve(null))
      })
    )).then(results => {
      const geos = results.filter((g): g is THREE.BufferGeometry => g !== null)
      if (geos.length === 0) return
      if (cancelled) {
        geos.forEach(g => g.dispose())
        return
      }

      const result = geos.map(geo => {
        geo.computeBoundingBox()
        const box = geo.boundingBox!
        // centre each piece on its own origin and sit it on the floor; where
        // it goes from there is the layout's business
        geo.translate(
          -(box.max.x + box.min.x) / 2,
          -(box.max.y + box.min.y) / 2,
          -box.min.z,
        )
        return {
          geo,
          edges: new THREE.EdgesGeometry(geo, 30),
          size: { w: box.max.x - box.min.x, d: box.max.y - box.min.y },
        }
      })

      loadedPieces = result
      setPieces(result)
    })

    return () => {
      cancelled = true
      loadedPieces.forEach(p => { p.geo.dispose(); p.edges.dispose() })
    }
  }, [urls])

  const offsets = useMemo(
    () => layOutCutField(pieces.map(p => p.size), cols, rows, SPLIT_PIECE_GAP_MM),
    [pieces, cols, rows],
  )

  // the camera fits once on load, but the field can be several times the size
  // of a single bin and changes shape with the bed size, so ask for a refit
  useEffect(() => {
    if (pieces.length === 0) return
    const t = setTimeout(
      () => window.dispatchEvent(new CustomEvent('bin-preview-view', { detail: 'fit' })),
      50,
    )
    return () => clearTimeout(t)
  }, [pieces, offsets])

  if (pieces.length === 0) return null

  return (
    <group rotation={[-Math.PI / 2, 0, 0]}>
      {pieces.map((piece, i) => (
        <group key={i} position={[offsets[i].x, offsets[i].y, 0]}>
          {renderMode === 'solid' ? (
            <>
              <mesh geometry={piece.geo}>
                <meshStandardMaterial color={SPLIT_PIECE_COLORS[i % SPLIT_PIECE_COLORS.length]} metalness={0} roughness={0.7} />
              </mesh>
              <lineSegments geometry={piece.edges}>
                <lineBasicMaterial color="#1e3d5c" linewidth={1} />
              </lineSegments>
            </>
          ) : (
            <>
              <mesh geometry={piece.geo}>
                <meshStandardMaterial color="#27272a" metalness={0} roughness={1} transparent opacity={0.3} />
              </mesh>
              <lineSegments geometry={piece.edges}>
                <lineBasicMaterial color={SPLIT_PIECE_COLORS[i % SPLIT_PIECE_COLORS.length]} linewidth={1} />
              </lineSegments>
            </>
          )}
        </group>
      ))}
    </group>
  )
}

// sits inside <Bounds>, listens for view commands via custom event
function CameraController() {
  const bounds = useBounds()
  const { camera } = useThree()
  const controls = useThree(s => s.controls) as any
  const fittedRef = useRef(false)

  // fit once on initial load only
  useEffect(() => {
    if (fittedRef.current) return
    fittedRef.current = true
    const t = setTimeout(() => bounds.refresh().fit(), 50)
    return () => clearTimeout(t)
  }, [bounds])

  useEffect(() => {
    function handleView(e: Event) {
      const view = (e as CustomEvent<CameraView>).detail
      const dist = camera.position.length() || 200

      switch (view) {
        case 'home':
          camera.position.set(0, dist * 0.7, dist * 0.7)
          break
        case 'top':
          camera.position.set(0, dist, 0.01)
          break
        case 'front':
          camera.position.set(0, 0.01, dist)
          break
        case 'right':
          camera.position.set(dist, 0.01, 0.01)
          break
        case 'fit':
          bounds.refresh().fit()
          return
      }

      camera.lookAt(0, 0, 0)
      controls?.update?.()
    }

    window.addEventListener('bin-preview-view', handleView)
    return () => window.removeEventListener('bin-preview-view', handleView)
  }, [bounds, camera, controls])

  return null
}

// floor grid drawn at the configured print bed size, so the preview shows
// whether the bin (or a split part) fits on the bed
function GridFloor({ bedSize }: { bedSize: number }) {
  const divisions = Math.max(2, Math.round(bedSize / GRID_CELL_MM))
  return (
    <gridHelper
      args={[bedSize, divisions, '#3f3f46', '#27272a']}
      rotation={[0, 0, 0]}
      position={[0, 0, 0]}
    />
  )
}

function LoadingFallback() {
  return (
    <mesh>
      <boxGeometry args={[20, 20, 20]} />
      <meshStandardMaterial color="#3f3f46" wireframe />
    </mesh>
  )
}

const viewButtons: { view: CameraView; icon: typeof Box; label: string }[] = [
  { view: 'home', icon: RotateCcw, label: 'Home' },
  { view: 'top', icon: ArrowUp, label: 'Top' },
  { view: 'front', icon: CircleDot, label: 'Front' },
  { view: 'right', icon: ArrowRight, label: 'Right' },
  { view: 'fit', icon: Box, label: 'Fit' },
]

export function BinPreview3D({
  stlUrl,
  splitUrls,
  insertUrl,
  bedSize = DEFAULT_BED_SIZE,
  splitCols = 0,
  splitRows = 0,
}: Props) {
  const [renderMode, setRenderMode] = useState<RenderMode>('solid')
  const bed = bedSize > 0 ? bedSize : DEFAULT_BED_SIZE
  const dispatchView = useCallback((view: CameraView) => {
    window.dispatchEvent(new CustomEvent('bin-preview-view', { detail: view }))
  }, [])

  return (
    <div className="w-full h-full min-h-[400px] relative">
      <Canvas
        camera={{ position: [0, 250, 250], fov: 50 }}
        style={{ background: '#0d0d0f' }}
      >
        <hemisphereLight args={['#e8f8ff', '#8899aa', 1.4]} />
        <directionalLight position={[5, 10, 5]} intensity={0.7} />

        <Suspense fallback={<LoadingFallback />}>
          <Bounds clip margin={1.15}>
            {splitUrls && splitUrls.length > 0 ? (
              <SplitModels urls={splitUrls} renderMode={renderMode} cols={splitCols} rows={splitRows} />
            ) : (
              <StlModel url={stlUrl} renderMode={renderMode} />
            )}
            {insertUrl && <StlModel url={insertUrl} renderMode={renderMode} color="#ff8844" edgeColor="#7a3310" />}
            <CameraController />
          </Bounds>
        </Suspense>

        <GridFloor bedSize={bed} />
        <GizmoHelper alignment="bottom-right" margin={[60, 60]}>
          <GizmoViewport labelColor="white" axisHeadScale={0.8} />
        </GizmoHelper>
        <OrbitControls
          enablePan={true}
          enableZoom={true}
          enableRotate={true}
          minDistance={50}
          maxDistance={Math.max(500, bed * 3)}
          makeDefault
        />
      </Canvas>

      <div className="absolute top-3 left-3 flex gap-1">
        {viewButtons.map(({ view, icon: Icon, label }) => (
          <button
            key={view}
            onClick={() => dispatchView(view)}
            className="p-1.5 rounded bg-surface/80 hover:bg-elevated text-text-secondary hover:text-text-primary transition-colors"
            title={label}
          >
            <Icon className="w-4 h-4" />
          </button>
        ))}
        <div className="w-px bg-border mx-0.5" />
        <button
          onClick={() => setRenderMode(m => m === 'solid' ? 'edges' : 'solid')}
          className={`p-1.5 rounded transition-colors ${
            renderMode === 'edges'
              ? 'bg-accent-muted text-accent'
              : 'bg-surface/80 hover:bg-elevated text-text-secondary hover:text-text-primary'
          }`}
          title="Toggle edges"
        >
          <Triangle className="w-4 h-4" />
        </button>
      </div>
    </div>
  )
}
